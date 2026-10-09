'use strict';

/* M6-02 SD2：回答展示与交互。
 *
 * 在 SD1（托管与输入）之上补齐：HTTP 状态与业务 status 共同判定、成功／空命中／字段校验失败／
 * 服务端失败的展示、来源展开、运行记录下载与文本安全渲染。
 *
 * 约定：
 * - 所有 Query、模型输出、来源与错误文本都用 textContent 写入，绝不当 HTML 执行；
 * - 不持久化历史或凭据（页面不写本地存储或 cookie），新请求开始即清除旧回答与旧下载目标；
 * - 不自动重试模型请求，失败后保留输入供用户手动重试。
 */

const SNAPSHOT_DATE = '2026-09-15';
const DEFAULT_TOP_K = 4;
// 示例只填入既有的 Development Query（Q002），点提交才会真正发起请求。
const EXAMPLE_QUERY =
  '声学扫描发现塑封空洞 molding void，涉及客户 CUS_001、产品 PROD_013、' +
  '生产批 DEV_PL_012、客户批 DEV_CL_012，需要查找历史调查记录。';

// 核心业务状态（与 casetrace.answer.cli 一致）；HTTP 边界状态另见 STATUS_LABELS。
const STATUS_OK = 'ok';
const STATUS_NO_HITS = 'no_hits';

const STATUS_LABELS = {
  ok: '成功',
  no_hits: '无候选历史案例',
  model_failed: '模型调用失败',
  format_failed: '模型返回格式不符合回答契约',
  citation_failed: '引用校验失败',
  service_unavailable: '服务端数据库前提不可用',
  internal_error: '服务端未预期错误',
};

// 运行记录里的字段名 → 中文标签；未登记的键直接显示原键名。
const CONTEXT_LABELS = {
  case_id: 'Case', abnormal_description: '异常描述',
  root_cause: '历史原因（该 Case 结案确认）', corrective_action: '历史改善措施',
  investigation_others: '其它调查记录', abnormal_processes: '已确认异常工序',
  detail_id: 'Detail', product_id: '产品', customer_lot: '客户批', production_lot: '生产批',
  production_time: '生产时间', detection_stage: '发现阶段', detection_time: '发现时间',
  abnormal_types: '异常类型', affected_qty: '涉及数量', disposition: '处置',
  checkpoint_id: 'Checkpoint', checkpoint_type: '检查类型', custom_name: '检查名称',
  result: '检查结果', relevance: '相关标记',
  sheet: '来源表', failure_mode_id: 'Failure Mode', closure_status: '结案状态',
  product_name: '产品名称', product_family: '产品族', package_route: '封装路线',
  customer_id: '客户', process_id: '工序', process_name: '工序名称',
};

const form = document.getElementById('answer-form');
const queryInput = document.getElementById('query');
const knownAtInput = document.getElementById('known-at');
const topKInput = document.getElementById('top-k');
const submitButton = document.getElementById('submit-button');
const exampleButton = document.getElementById('example-button');
const statusLine = document.getElementById('status');
const resultBody = document.getElementById('result-body');
const downloadButton = document.getElementById('download-button');

// 请求进行中标记：用于兜底阻止重复提交（控件本身也会被禁用）。
let inFlight = false;
// 当前下载对象 URL；替换或清除时必须 revoke，避免泄漏。
let downloadUrl = null;

// ── 基础工具 ───────────────────────────────────────────────────────────────

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/** 创建元素；文本一律走 textContent，避免把数据当 HTML。 */
function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  if (text !== undefined && text !== null) {
    element.textContent = String(text);
  }
  return element;
}

function formatValue(value) {
  if (Array.isArray(value)) {
    return value.length ? value.map(formatValue).join('、') : '（空）';
  }
  if (isObject(value)) {
    return JSON.stringify(value);
  }
  if (value === null || value === undefined) {
    return '（空）';
  }
  return String(value);
}

function textList(items, className) {
  const list = node('ul', className || 'text-list');
  const values = Array.isArray(items) ? items : [];
  if (!values.length) {
    list.append(node('li', 'empty', '（无）'));
    return list;
  }
  for (const item of values) {
    list.append(node('li', null, formatValue(item)));
  }
  return list;
}

/** 一行「标签 + 值」；value 可以是字符串，也可以是已经构造好的元素。 */
function fieldBlock(label, value, hint) {
  const wrap = node('div', 'field-block');
  wrap.append(node('div', 'field-label', label));
  if (value instanceof Node) {
    wrap.append(value);
  } else {
    wrap.append(node('p', 'field-value', formatValue(value)));
  }
  if (hint) {
    wrap.append(node('p', 'hint', hint));
  }
  return wrap;
}

// ── 状态与下载 ─────────────────────────────────────────────────────────────

function setStatus(text, kind) {
  statusLine.textContent = text;
  statusLine.dataset.kind = kind || 'info';
}

function setBusy(busy) {
  inFlight = busy;
  for (const element of [queryInput, knownAtInput, topKInput, submitButton, exampleButton]) {
    element.disabled = busy;
  }
  submitButton.textContent = busy ? '请求中…' : '提交请求';
}

function clearDownload() {
  if (downloadUrl) {
    // 释放上一次的下载对象 URL，避免内存泄漏。
    URL.revokeObjectURL(downloadUrl);
    downloadUrl = null;
  }
  downloadButton.hidden = true;
  downloadButton.removeAttribute('href');
  downloadButton.removeAttribute('download');
  downloadButton.textContent = '下载本次运行记录（JSON）';
}

function downloadName(record, status) {
  const query = isObject(record.query) ? record.query : {};
  const knownAt = typeof query.known_at === 'string' && query.known_at ? query.known_at : 'record';
  return `casetrace-${status || 'record'}-${knownAt}.json`;
}

function setDownload(record, label, status) {
  clearDownload();
  // 内容保持 API 返回值本身，不在这里改写或裁剪。
  const blob = new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' });
  downloadUrl = URL.createObjectURL(blob);
  downloadButton.href = downloadUrl;
  downloadButton.download = downloadName(record, status);
  downloadButton.textContent = label;
  downloadButton.hidden = false;
}

function clearResult() {
  // 新请求开始即清除旧回答与旧下载目标，保证展示始终对应本次提交。
  resultBody.replaceChildren();
  clearDownload();
}

// ── 结果判定：HTTP 状态与业务 status 共同决定 ─────────────────────────────

// 只检查成功展示所需的结构；字段缺失不能冒充合法的零采用或空命中。
function hasReadableAnswer(record, status) {
  return isObject(record) && record.status === status
    && isObject(record.query) && typeof record.query.text === 'string'
    && typeof record.query.known_at === 'string'
    && Array.isArray(record.ranking) && isObject(record.answer)
    && Array.isArray(record.answer.case_answers)
    && typeof record.answer.insufficiency === 'string'
    && (status !== STATUS_OK || (
      Array.isArray(record.answer.skipped_candidates)
      && Array.isArray(record.answer.current_gaps)
      && isObject(record.context) && Array.isArray(record.context.cases)
    ));
}

function present(httpStatus, body) {
  const status = typeof body.status === 'string' ? body.status : '';
  const message = typeof body.message === 'string' ? body.message : '';
  const record = isObject(body.record) ? body.record : null;

  if (httpStatus === 200 && (status === STATUS_OK || status === STATUS_NO_HITS)
    && !hasReadableAnswer(record, status)) {
    renderUnreadable(`运行记录结构不完整（HTTP ${httpStatus}）`,
      `服务端返回 status=${status}，但记录缺少展示所需字段或状态不一致，本次未得到可用结果。`);
    setStatus(`HTTP ${httpStatus}｜status=${status}｜运行记录结构不完整。`, 'error');
    return;
  }
  if (httpStatus === 200 && status === STATUS_OK) {
    renderSuccess(record);
    setStatus(`HTTP 200｜status=ok${message ? `｜${message}` : ''}`, 'ok');
    return;
  }
  if (httpStatus === 200 && status === STATUS_NO_HITS) {
    renderNoHits(record);
    setStatus('HTTP 200｜status=no_hits｜本次检索没有候选历史案例，未调用模型；'
      + '这不是运行故障，也不表示已确认「没有相关案例」。', 'warning');
    return;
  }
  if (httpStatus === 422) {
    renderValidationFailure(body);
    setStatus('HTTP 422｜请求字段校验失败：输入已保留，请按提示修改后重新提交。', 'error');
    return;
  }
  if (status) {
    renderFailure(httpStatus, status, message, record);
    setStatus(`HTTP ${httpStatus}｜status=${status}${message ? `｜${message}` : ''}`, 'error');
    return;
  }
  renderUnreadable(`响应结构无法识别（HTTP ${httpStatus}）`,
    '服务端返回的内容没有可识别的 status 字段，本次未得到可用结果。');
  setStatus(`HTTP ${httpStatus}｜响应结构无法识别。`, 'error');
}

// ── 成功：结构化回答 ───────────────────────────────────────────────────────

function renderSuccess(record) {
  const fragment = document.createDocumentFragment();
  fragment.append(renderRunSummary(record));
  const answer = isObject(record.answer) ? record.answer : {};
  fragment.append(renderAdoptedCases(record, answer.case_answers));
  fragment.append(renderRanking(record.ranking));
  fragment.append(renderSkipped(answer.skipped_candidates));
  fragment.append(renderGaps(answer.current_gaps, answer.insufficiency));
  resultBody.replaceChildren(fragment);
  setDownload(record, '下载本次运行记录（JSON）', record.status || STATUS_OK);
}

function renderRunSummary(record) {
  const section = node('section', 'block');
  section.append(node('h3', null, '本次请求'));
  const query = isObject(record.query) ? record.query : {};
  const snapshot = isObject(record.snapshot) ? record.snapshot : {};
  const retrieval = isObject(record.retrieval) ? record.retrieval : {};
  const corpus = isObject(record.corpus) ? record.corpus : {};

  const grid = node('div', 'summary-grid');
  grid.append(fieldBlock('Query 原文', query.text || '（未提供）'));
  grid.append(fieldBlock('快照时点 known_at', query.known_at || snapshot.known_at || '（未提供）'));
  grid.append(fieldBlock('快照 ID', snapshot.snapshot_id || '（未提供）'));
  grid.append(fieldBlock('检索方法与候选数',
    `${retrieval.requested_method || '（未提供）'}／top_k=${formatValue(retrieval.top_k)}`));
  if (typeof corpus.case_count === 'number') {
    grid.append(fieldBlock('语料规模', `${corpus.case_count} 条历史 Case`));
  }
  section.append(grid);
  section.append(node('p', 'hint',
    '下列内容全部对应本次提交；历史原因与历史措施是该历史 Case 的结案记录，'
    + '不是当前 Incident 的最终结论，也不是当前建议。'));
  return section;
}

function renderAdoptedCases(record, caseAnswers) {
  const items = Array.isArray(caseAnswers) ? caseAnswers : [];
  const section = node('section', 'block');
  section.append(node('h3', null, `采用的历史案例（${items.length}）`));
  if (!items.length) {
    // 零采用是明确的成功结果，不是请求失败。
    section.append(node('p', 'callout', '本次未采用历史案例：模型没有给出可采用的案例。'
      + '这不是请求失败；下方仍列出本次的信息不足。'));
    return section;
  }
  const cards = node('div', 'cards');
  for (const item of items) {
    cards.append(renderCaseCard(record, item));
  }
  section.append(cards);
  return section;
}

function renderCaseCard(record, item) {
  const data = isObject(item) ? item : {};
  const card = node('article', 'card');

  const header = node('div', 'card-header');
  header.append(node('span', 'badge', formatValue(data.case_id)));
  header.append(node('span', 'tag', '历史案例（非当前结论）'));
  card.append(header);

  card.append(fieldBlock('相关性说明（为什么值得查看）', data.relevance_reason));
  card.append(fieldBlock('当前侧已知事实', textList(data.query_facts)));
  card.append(fieldBlock('历史侧事实', textList(data.case_facts)));
  card.append(fieldBlock('历史原因（该 Case 结案确认，不是当前 Incident 结论）',
    data.historical_root_cause, '不要据此判定当前异常的原因。'));
  card.append(renderEvidences(data.historical_evidences));
  card.append(fieldBlock('历史改善措施（当时的处置，不是当前建议）', data.historical_corrective_action));
  card.append(renderSources(record, data.sources));
  return card;
}

function renderEvidences(evidences) {
  const items = Array.isArray(evidences) ? evidences : [];
  if (!items.length) {
    return fieldBlock('历史检查结果（checkpoint / result）',
      node('p', 'hint', '本次没有可展开的历史检查结果。'));
  }
  const list = node('div', 'evidence-list');
  for (const item of items) {
    const entry = isObject(item) ? item : {};
    const wrap = node('div', 'evidence');
    wrap.append(node('span', 'mono', entry.checkpoint_id || '（无 checkpoint_id）'));
    wrap.append(node('p', 'field-value', entry.result || '（无结果文本）'));
    list.append(wrap);
  }
  return fieldBlock('历史检查结果（checkpoint / result）', list);
}

// ── 来源与原始上下文（默认折叠） ───────────────────────────────────────────

function contextCase(record, caseId) {
  const context = isObject(record.context) ? record.context : {};
  const cases = Array.isArray(context.cases) ? context.cases : [];
  for (const entry of cases) {
    if (isObject(entry) && entry.case_id === caseId) {
      return entry;
    }
  }
  return null;
}

function renderObject(data) {
  const dl = node('dl', 'kv');
  const entries = Object.entries(isObject(data) ? data : {});
  for (const [key, value] of entries) {
    if (value === null || value === undefined || value === '') {
      continue;
    }
    dl.append(node('dt', null, CONTEXT_LABELS[key] || key));
    dl.append(node('dd', null, formatValue(value)));
  }
  if (!dl.childElementCount) {
    dl.append(node('dd', 'empty', '（无字段）'));
  }
  return dl;
}

function renderObjectList(items) {
  const list = Array.isArray(items) ? items : [];
  if (!list.length) {
    return node('p', 'hint', '（无）');
  }
  const wrap = node('div', 'object-list');
  for (const item of list) {
    wrap.append(renderObject(item));
  }
  return wrap;
}

function renderContextCase(record, caseId) {
  const details = node('details', 'context-case');
  details.append(node('summary', null, `原始上下文：${caseId}`));
  const entry = contextCase(record, caseId);
  if (!entry) {
    details.append(node('p', 'hint',
      `本次运行记录的上下文中没有 ${caseId} 的条目，无法展开原始 Case。`));
    return details;
  }
  details.append(fieldBlock('Case（历史原文）', renderObject(entry.case)));
  details.append(fieldBlock('Detail（生产与发现事实）', renderObjectList(entry.details)));
  details.append(fieldBlock('Evidence（检查结果）', renderObjectList(entry.evidences)));
  details.append(fieldBlock('来源记录（允许进入上下文的字段）', renderObject(entry.source)));
  details.append(fieldBlock('产品背景', renderObjectList(entry.background)));
  details.append(fieldBlock('已确认异常工序', renderObjectList(entry.processes)));
  return details;
}

function renderSources(record, sources) {
  const items = Array.isArray(sources) ? sources : [];
  const details = node('details', 'sources');
  details.append(node('summary', null,
    items.length ? `来源与原始上下文（${items.length} 处来源）` : '来源与原始上下文（无来源）'));
  if (!items.length) {
    details.append(node('p', 'hint', '本次回答没有列出可展开的来源。'));
    return details;
  }

  const list = node('ul', 'source-list');
  for (const item of items) {
    const source = isObject(item) ? item : {};
    list.append(node('li', null, `${formatValue(source.case_id)} · ${formatValue(source.field)}`));
  }
  details.append(list);

  // 每个被引用的 Case 展开一次它的完整上下文（不新建通用引用解析器）。
  const seen = new Set();
  for (const item of items) {
    const source = isObject(item) ? item : {};
    const caseId = source.case_id;
    if (typeof caseId !== 'string' || seen.has(caseId)) {
      continue;
    }
    seen.add(caseId);
    details.append(renderContextCase(record, caseId));
  }
  return details;
}

// ── 候选、不足与失败 ───────────────────────────────────────────────────────

function renderRanking(ranking) {
  const items = Array.isArray(ranking) ? ranking : [];
  const section = node('section', 'block');
  section.append(node('h3', null, `检索候选排名（${items.length}）`));
  section.append(node('p', 'hint',
    '这是 R3 检索给出的候选顺序，与模型是否采用某个案例无关；'
    + '分数只是排序依据，不是相关概率，也不能当作置信度。'));
  if (!items.length) {
    section.append(node('p', 'hint', '本次没有检索候选。'));
    return section;
  }
  const table = node('table', 'ranking-table');
  const headRow = node('tr');
  for (const label of ['排名', 'Case', '分数', '命中词项']) {
    headRow.append(node('th', null, label));
  }
  const thead = node('thead');
  thead.append(headRow);
  table.append(thead);

  const tbody = node('tbody');
  for (const item of items) {
    const entry = isObject(item) ? item : {};
    const row = node('tr');
    row.append(node('td', null, formatValue(entry.rank)));
    row.append(node('td', null, formatValue(entry.case_id)));
    row.append(node('td', 'mono', formatValue(entry.score)));
    row.append(node('td', null, formatValue(entry.matched_terms)));
    tbody.append(row);
  }
  table.append(tbody);
  section.append(table);
  return section;
}

function renderSkipped(skipped) {
  const items = Array.isArray(skipped) ? skipped : [];
  const section = node('section', 'block');
  section.append(node('h3', null, `未采用的候选（${items.length}）`));
  section.append(node('p', 'hint',
    '这些候选本次未被采用；理由由模型按本次证据给出，不代表它们与当前异常无关。'));
  if (!items.length) {
    section.append(node('p', 'hint', '本次没有排除的候选。'));
    return section;
  }
  const cards = node('div', 'cards');
  for (const item of items) {
    const entry = isObject(item) ? item : {};
    const card = node('article', 'card');
    const header = node('div', 'card-header');
    header.append(node('span', 'badge muted', formatValue(entry.case_id)));
    header.append(node('span', 'tag', '未采用'));
    card.append(header);
    card.append(node('p', 'field-value', entry.reason || '（未提供理由）'));
    cards.append(card);
  }
  section.append(cards);
  return section;
}

function renderGaps(gaps, insufficiency) {
  const section = node('section', 'block');
  section.append(node('h3', null, '当前信息不足'));
  if (typeof insufficiency === 'string' && insufficiency) {
    section.append(node('p', 'callout', insufficiency));
  } else {
    section.append(node('p', 'hint', '本次回答没有给出整体不足说明。'));
  }
  const items = Array.isArray(gaps) ? gaps : [];
  if (items.length) {
    section.append(node('h4', null, '具体缺口'));
    section.append(textList(items, 'text-list'));
  } else {
    section.append(node('p', 'hint', '本次没有列出具体缺口。'));
  }
  return section;
}

function renderNoHits(record) {
  const fragment = document.createDocumentFragment();
  fragment.append(renderRunSummary(record));
  const answer = isObject(record.answer) ? record.answer : {};
  const section = node('section', 'block');
  section.append(node('h3', null, '无候选历史案例'));
  section.append(node('p', 'callout warning',
    '本次检索没有返回候选历史案例，服务端没有调用模型。这不是请求失败，'
    + '也不表示已确认「没有相关案例」。'));
  if (typeof answer.insufficiency === 'string' && answer.insufficiency) {
    section.append(node('p', 'field-value', answer.insufficiency));
  }
  fragment.append(section);
  fragment.append(renderRanking(record.ranking));
  resultBody.replaceChildren(fragment);
  // 空命中仍有完整运行记录，可以下载。
  setDownload(record, '下载本次运行记录（JSON）', record.status || STATUS_NO_HITS);
}

function renderValidationFailure(body) {
  const section = node('section', 'block');
  section.append(node('h3', null, '请求字段校验失败（HTTP 422）'));
  section.append(node('p', 'callout error',
    '请求没有通过字段校验：服务端没有读取数据库、也没有构造模型。输入已保留，请修改后重试。'));
  const details = Array.isArray(body.detail) ? body.detail : [];
  const list = node('ul', 'text-list');
  if (details.length) {
    for (const item of details) {
      const entry = isObject(item) ? item : {};
      const location = Array.isArray(entry.loc) ? entry.loc.join('.') : '';
      list.append(node('li', null,
        `${location ? `${location}：` : ''}${formatValue(entry.msg || entry)}`));
    }
  } else {
    list.append(node('li', null, formatValue(body.detail || '（服务端未提供字段详情）')));
  }
  section.append(list);
  resultBody.replaceChildren(section);
  // 422 没有运行记录，不提供下载。
  clearDownload();
}

function renderFailure(httpStatus, status, message, record) {
  const fragment = document.createDocumentFragment();
  const section = node('section', 'block');
  section.append(node('h3', null, `本次请求未成功：${STATUS_LABELS[status] || '服务端失败'}`));
  section.append(node('p', 'callout error',
    message || '服务端返回了失败状态，但没有提供安全说明。'));

  const grid = node('div', 'summary-grid');
  grid.append(fieldBlock('HTTP 状态', String(httpStatus)));
  grid.append(fieldBlock('业务状态 status', status));
  const errorType = isObject(record) && isObject(record.error) ? record.error.type : null;
  if (typeof errorType === 'string' && errorType) {
    grid.append(fieldBlock('错误类型', errorType));
  }
  section.append(grid);
  section.append(node('p', 'hint', isObject(record)
    ? '本次运行记录保留了失败证据；即使记录里有模型返回文本，也不作为成功回答展示。'
    : '本次没有可读取的运行记录。'));
  fragment.append(section);
  resultBody.replaceChildren(fragment);
  if (isObject(record)) {
    setDownload(record, '下载失败记录（JSON）', status || String(httpStatus));
  } else {
    clearDownload();
  }
}

function renderUnreadable(heading, note) {
  const section = node('section', 'block');
  section.append(node('h3', null, heading));
  section.append(node('p', 'callout error', note));
  section.append(node('p', 'hint', '输入已保留，可手动重试；页面不会自动重试模型请求。'));
  resultBody.replaceChildren(section);
  clearDownload();
}

// ── 表单与请求 ─────────────────────────────────────────────────────────────

function fillExample() {
  queryInput.value = EXAMPLE_QUERY;
  queryInput.focus();
}

/** 把表单读成 API 契约的三字段；不合法时返回 { error, focus }。 */
function readForm() {
  const query = queryInput.value;
  if (!query.trim()) {
    return { error: 'Query 不能为空：请填写当前已知异常后再提交。', focus: queryInput };
  }
  const knownAt = knownAtInput.value;
  if (!knownAt) {
    return { error: '请选择快照日期（当前仅支持 2026-09-15）。', focus: knownAtInput };
  }
  const topK = Number(topKInput.value.trim());
  if (!Number.isInteger(topK) || topK <= 0) {
    return { error: 'top_k 必须是正整数。', focus: topKInput };
  }
  return { request: { query, known_at: knownAt, top_k: topK } };
}

async function submitAnswer(event) {
  event.preventDefault();
  if (inFlight) {
    return;
  }
  const parsed = readForm();
  if (parsed.error) {
    setStatus(parsed.error, 'error');
    parsed.focus.focus();
    return;
  }

  clearResult();
  setBusy(true);
  setStatus('已提交，等待服务端返回…', 'pending');

  let response;
  let text;
  try {
    response = await fetch('/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parsed.request),
    });
    text = await response.text();
  } catch (error) {
    // 网络中断：不自动重试模型请求，保留输入供用户手动重试。
    renderUnreadable('网络请求失败', '本次未得到可用响应，请确认服务是否运行后重试。');
    setStatus('网络请求失败：本次未得到可用响应。', 'error');
    setBusy(false);
    return;
  }

  let body = null;
  try {
    body = JSON.parse(text);
  } catch (error) {
    body = null;
  }
  if (!isObject(body)) {
    renderUnreadable(`无法解析服务端响应（HTTP ${response.status}）`,
      '服务端返回的不是 JSON 对象，本次未得到可用结果。');
    setStatus(`HTTP ${response.status}｜响应不是可解析的 JSON。`, 'error');
    setBusy(false);
    return;
  }

  try {
    present(response.status, body);
  } catch (error) {
    // 渲染意外失败也不把页面留在半成品状态。
    renderUnreadable('页面处理响应时出错', '本次未得到可用结果，输入已保留，可手动重试。');
    setStatus('页面处理响应时出错：本次未得到可用结果。', 'error');
  } finally {
    setBusy(false);
  }
}

form.addEventListener('submit', submitAnswer);
exampleButton.addEventListener('click', fillExample);

// 初始值固定为服务端支持的快照与默认 top_k；初次加载不自动提交。
knownAtInput.value = SNAPSHOT_DATE;
topKInput.value = String(DEFAULT_TOP_K);
