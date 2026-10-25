export interface ReportDocumentData {
  caseFile: any;
  evidence: any[];
  anomalies: any[];
  reconstructions: any[];
  graphData: any;
  summaryData: any;
}

const escapeHtml = (value: unknown) => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#039;');

const listItems = (items: unknown[], emptyLabel: string) => items.length
  ? items.map(item => `<li>${escapeHtml(typeof item === 'string' ? item : JSON.stringify(item))}</li>`).join('')
  : `<li>${escapeHtml(emptyLabel)}</li>`;

export const buildReportPages = ({ caseFile, evidence, anomalies, reconstructions, graphData, summaryData }: ReportDocumentData) => {
  const title = caseFile?.title || 'Untitled Investigation';
  const generatedAt = new Date().toLocaleString();
  const complexity = summaryData?.complexity;

  return [`<div class="report-cover">
<p class="report-kicker">AIMCR | DIGITAL FORENSICS UNIT</p>
<div class="report-rule"></div>
<h1>Forensic Investigation<br>Report</h1>
<p class="report-cover-title">${escapeHtml(title)}</p>
<div class="report-cover-meta"><p>Prepared for case review</p><p>Submitted by: ${escapeHtml(caseFile?.investigator_name || 'Assigned Investigator')}</p><p>Generated: ${escapeHtml(generatedAt)}</p></div>
<p class="report-classification">CONFIDENTIAL INVESTIGATIVE WORK PRODUCT</p>
</div>`, `<p class="report-kicker">CASE DOCUMENTATION</p>
<h2>Case Identification</h2>
<table><tbody>
<tr><th>Case title</th><td>${escapeHtml(title)}</td></tr>
<tr><th>Case ID</th><td>${escapeHtml(caseFile?.id)}</td></tr>
<tr><th>Priority</th><td>${escapeHtml(caseFile?.priority || 'Medium')}</td></tr>
<tr><th>Report generated</th><td>${escapeHtml(generatedAt)}</td></tr>
</tbody></table>
<h2>Executive Summary</h2>
<p>${escapeHtml(complexity?.explanation || 'This report presents the evidence and intelligence currently available for the selected case. The investigator should review, edit, and approve the findings before final submission.')}</p>
<h2>Scope and Methodology</h2>
<p>The investigation record was assembled from uploaded case evidence and the AIMCR analysis modules. Findings should be interpreted alongside the original evidence, audit trail, and applicable investigative procedures.</p>`, `<p class="report-kicker">ANALYTICAL FINDINGS</p>
<h2>Investigation Metrics</h2>
<ul>
<li>Forensic artifacts examined: ${evidence.length}</li>
<li>Flagged anomalies: ${anomalies.length}</li>
<li>Reconstructed scenarios: ${reconstructions.length}</li>
<li>Network connections identified: ${graphData?.edges?.length || 0}</li>
</ul>
${complexity ? `<h2>Forensic Complexity Assessment</h2><p>Rating: <strong>${escapeHtml(complexity.rating)}</strong> (${escapeHtml(complexity.score)}/100)</p><p>${escapeHtml(complexity.explanation)}</p>` : ''}
<h2>Key Findings</h2>
<ol>${listItems(anomalies.slice(0, 12).map(item => item.explanation || item.description || item.type), 'No anomalies have been recorded.')}</ol>`, `<p class="report-kicker">EVENT RECONSTRUCTION</p>
<h2>Reconstructed Scenarios</h2>
<ol>${listItems(reconstructions.slice(0, 12).map(item => `${item.incident_type || 'Scenario'}: ${item.explanation || 'No explanation provided.'}`), 'No reconstructed scenarios have been recorded.')}</ol>
<h2>Evidence Register</h2>
<p>${evidence.length} normalized evidence record(s) are associated with this case. Confirm the original evidence identifiers and chain-of-custody details before publication.</p>
<h2>Investigator Conclusions</h2>
<p>Record the supported conclusion, limitations, and recommended next steps in this section.</p>`, `<p class="report-kicker">INVESTIGATOR WORKSHEET</p>
<h2>Investigator Notes</h2>
<p>Use this page for additional observations, evidence references, conclusions, and recommended next steps.</p>
<p><br><br><br><br><br><br></p>
<h2>Review and Approval</h2>
<table><tbody><tr><th>Reviewed by</th><td></td></tr><tr><th>Review date</th><td></td></tr><tr><th>Approval / signature</th><td></td></tr></tbody></table>`];
};

export const buildReportHtml = (data: ReportDocumentData) => buildReportPages(data).join('<div style="page-break-after:always"></div>');

/* Legacy single-document content remains available to callers that export directly. */
export const buildLegacyReportHtml = ({ caseFile, evidence, anomalies, reconstructions, graphData, summaryData }: ReportDocumentData) => {
  const title = caseFile?.title || 'Untitled Investigation';
  const generatedAt = new Date().toLocaleString();
  const complexity = summaryData?.complexity;
  return `<h1>Forensic Investigation Report</h1>
<p class="report-subtitle">AIMCR | Editable working document</p>
<hr>
<h2>Case File</h2>
<table><tbody>
<tr><th>Case title</th><td>${escapeHtml(title)}</td></tr>
<tr><th>Case ID</th><td>${escapeHtml(caseFile?.id)}</td></tr>
<tr><th>Priority</th><td>${escapeHtml(caseFile?.priority || 'Medium')}</td></tr>
<tr><th>Report generated</th><td>${escapeHtml(generatedAt)}</td></tr>
</tbody></table>
<h2>Executive Summary</h2>
<p>${escapeHtml(complexity?.explanation || 'This report is automatically populated from the evidence and intelligence currently available for this case. Review and edit the findings before final submission.')}</p>
<h2>Investigation Metrics</h2>
<ul>
<li>Forensic artifacts: ${evidence.length}</li>
<li>Flagged anomalies: ${anomalies.length}</li>
<li>Reconstructed scenarios: ${reconstructions.length}</li>
<li>Network connections: ${graphData?.edges?.length || 0}</li>
</ul>
${complexity ? `<h2>Forensic Complexity Assessment</h2><p>Rating: <strong>${escapeHtml(complexity.rating)}</strong> (${escapeHtml(complexity.score)}/100)</p><p>${escapeHtml(complexity.explanation)}</p>` : ''}
<h2>Key Findings</h2>
<ul>${listItems(anomalies.slice(0, 12).map(item => item.explanation || item.description || item.type), 'No anomalies have been recorded.')}</ul>
<h2>Reconstructed Scenarios</h2>
<ul>${listItems(reconstructions.slice(0, 12).map(item => `${item.incident_type || 'Scenario'}: ${item.explanation || 'No explanation provided.'}`), 'No reconstructed scenarios have been recorded.')}</ul>
<h2>Investigator Notes</h2>
<p>Add conclusions, evidence references, and recommended next steps here.</p>`;
};

export const downloadEditableWordDocument = (title: string, bodyHtml: string) => {
  const documentHtml = `<html><head><meta charset="utf-8"><style>body{font-family:Calibri,Arial,sans-serif;color:#1f2937;line-height:1.5}h1{font-size:24pt;color:#123b62}h2{font-size:15pt;color:#123b62;border-bottom:1px solid #cbd5e1;padding-bottom:4px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #cbd5e1;padding:7px;text-align:left}th{background:#eef3f8}.report-subtitle{color:#64748b}</style></head><body>${bodyHtml}</body></html>`;
  const blob = new Blob([documentHtml], { type: 'application/msword' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${title.replace(/[^a-z0-9]+/gi, '_') || 'investigation'}_report.doc`;
  anchor.click();
  URL.revokeObjectURL(url);
};
