/**
 * Tracker Agent — Google Apps Script
 *
 * Adds a "Tracker Agent" menu to the spreadsheet.
 * Select a Milestone row, click "Preview Update", and a sidebar opens
 * with an AI-generated Jira update you can edit and post.
 *
 * SETUP — Set these in Script Properties (Project Settings > Script Properties):
 *   OPENAI_API_KEY    - Your OpenAI API key
 *   JIRA_BASE_URL     - e.g. https://yourcompany.atlassian.net
 *   JIRA_EMAIL        - Your Jira account email
 *   JIRA_API_TOKEN    - Jira API token
 */

// --------------- Menu ---------------

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Tracker Agent')
    .addItem('Preview Update', 'showPreviewSidebar')
    .addToUi();
}

// --------------- Sidebar trigger ---------------

function showPreviewSidebar() {
  var sheet = SpreadsheetApp.getActiveSheet();
  var row = sheet.getActiveRange().getRow();

  if (row <= 1) {
    SpreadsheetApp.getUi().alert('Select a Milestone row first (not the header).');
    return;
  }

  var data = getRowData(sheet, row);

  if (data.workType !== 'Milestone') {
    SpreadsheetApp.getUi().alert(
      'Please select a Milestone row. You selected a "' + data.workType + '" row.'
    );
    return;
  }

  if (!data.jiraId) {
    SpreadsheetApp.getUi().alert('This milestone has no Jira ID.');
    return;
  }

  // Store selected row info so the sidebar can retrieve it
  var userProps = PropertiesService.getUserProperties();
  userProps.setProperty('SELECTED_ROW', JSON.stringify(data));

  var html = HtmlService.createHtmlOutputFromFile('Sidebar')
    .setTitle('Update Preview')
    .setWidth(420);
  SpreadsheetApp.getUi().showSidebar(html);
}

// --------------- Row parsing ---------------

/**
 * Read a single row and walk backwards to find its parent Track/Workstream.
 */
function getRowData(sheet, rowNum) {
  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  var values = sheet.getRange(rowNum, 1, 1, sheet.getLastColumn()).getValues()[0];

  var col = {};
  for (var i = 0; i < headers.length; i++) {
    col[headers[i]] = (values[i] || '').toString().trim();
  }

  // Walk backwards to find Track and Workstream
  var trackName = '';
  var trackStatus = '';
  var workstream = '';
  var notesLink = '';

  var allData = sheet.getRange(2, 1, rowNum - 1, sheet.getLastColumn()).getValues();
  for (var r = allData.length - 1; r >= 0; r--) {
    var rowDict = {};
    for (var c = 0; c < headers.length; c++) {
      rowDict[headers[c]] = (allData[r][c] || '').toString().trim();
    }
    if (!trackName && rowDict['WorkType'] === 'Track') {
      trackName = rowDict['Description'];
      trackStatus = rowDict['Status'];
      notesLink = rowDict['Notes'] || '';
    }
    if (!workstream && rowDict['WorkType'] === 'Workstream') {
      workstream = rowDict['Description'];
    }
    if (trackName && workstream) break;
  }

  // Collect sibling milestones under the same track
  var milestones = [];
  var inTrack = false;
  var fullData = sheet.getRange(2, 1, sheet.getLastRow() - 1, sheet.getLastColumn()).getValues();
  for (var r = 0; r < fullData.length; r++) {
    var rd = {};
    for (var c = 0; c < headers.length; c++) {
      rd[headers[c]] = (fullData[r][c] || '').toString().trim();
    }
    if (rd['WorkType'] === 'Track' && rd['Description'] === trackName) {
      inTrack = true;
      continue;
    }
    if (inTrack && rd['WorkType'] === 'Track') break; // next track
    if (inTrack && rd['WorkType'] === 'Workstream') break;
    if (inTrack && rd['WorkType'] === 'Milestone' && rd['Jira ID']) {
      milestones.push({
        name: rd['Description'],
        status: rd['Status'],
        target_date: rd['Target Date'],
        owner: rd['Milestone Owner'],
        jira_id: rd['Jira ID'],
        previous_status_update: rd['Status Update']
      });
    }
  }

  return {
    workType: col['WorkType'],
    description: col['Description'],
    jiraId: col['Jira ID'],
    status: col['Status'],
    targetDate: col['Target Date'],
    owner: col['Milestone Owner'],
    workstream: workstream,
    trackName: trackName,
    trackStatus: trackStatus,
    notesLink: notesLink,
    milestones: milestones
  };
}

// --------------- Called from Sidebar ---------------

function getSelectedRowData() {
  var json = PropertiesService.getUserProperties().getProperty('SELECTED_ROW');
  return json ? JSON.parse(json) : null;
}

function generatePreview(rowData) {
  var props = PropertiesService.getScriptProperties();
  var apiKey = props.getProperty('OPENAI_API_KEY');
  if (!apiKey) throw new Error('OPENAI_API_KEY not set in Script Properties.');

  // Fetch notes document text if link exists
  var notesText = 'No notes available.';
  if (rowData.notesLink) {
    try {
      notesText = getDocText(rowData.notesLink);
    } catch (e) {
      notesText = '[Error fetching notes: ' + e.message + ']';
    }
  }

  var milestonesJson = JSON.stringify(rowData.milestones, null, 2);

  var prompt =
    'You are a program management reporting agent.\n\n' +
    'You have been given:\n' +
    '1. A list of milestones for a project track\n' +
    '2. The full text of the track\'s notes document\n\n' +
    'Your job: Generate a structured Jira update for the milestone with jira_id "' + rowData.jiraId + '".\n\n' +
    'MILESTONES:\n' + milestonesJson + '\n\n' +
    'NOTES DOCUMENT:\n' + notesText + '\n\n' +
    'RULES:\n' +
    '- Map information from the notes document to the correct milestone.\n' +
    '- If the notes document does not mention the milestone, use its existing status and previous status update.\n' +
    '- Be factual. Do not invent progress that isn\'t supported by the notes.\n' +
    '- Keep each bullet point concise (one sentence).\n' +
    '- The leadership_summary should be a single executive-level sentence.\n\n' +
    'Return ONLY valid JSON in this exact format (no markdown, no explanation):\n\n' +
    '{\n' +
    '  "progress_summary": ["bullet 1", "bullet 2"],\n' +
    '  "recent_changes": ["bullet 1", "bullet 2"],\n' +
    '  "next_steps": ["bullet 1", "bullet 2"],\n' +
    '  "leadership_summary": "Single executive sentence."\n' +
    '}';

  var response = UrlFetchApp.fetch('https://api.openai.com/v1/chat/completions', {
    method: 'post',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + apiKey },
    payload: JSON.stringify({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.2
    })
  });

  var body = JSON.parse(response.getContentText());
  var content = body.choices[0].message.content.trim();

  // Strip markdown code fences if present
  if (content.indexOf('```') === 0) {
    content = content.substring(content.indexOf('\n') + 1);
    if (content.lastIndexOf('```') !== -1) {
      content = content.substring(0, content.lastIndexOf('```'));
    }
    content = content.trim();
  }

  return JSON.parse(content);
}

function postToJira(jiraId, comment) {
  var props = PropertiesService.getScriptProperties();
  var baseUrl = props.getProperty('JIRA_BASE_URL');
  var email = props.getProperty('JIRA_EMAIL');
  var token = props.getProperty('JIRA_API_TOKEN');

  if (!baseUrl || !email || !token) {
    throw new Error('Jira credentials not set in Script Properties.');
  }

  var url = baseUrl + '/rest/api/3/issue/' + jiraId + '/comment';
  var creds = Utilities.base64Encode(email + ':' + token);

  // Jira Cloud API v3 requires Atlassian Document Format (ADF)
  var payload = {
    body: {
      type: 'doc',
      version: 1,
      content: [{
        type: 'paragraph',
        content: [{ type: 'text', text: comment }]
      }]
    }
  };

  var response = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    headers: { 'Authorization': 'Basic ' + creds },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });

  var code = response.getResponseCode();
  if (code !== 200 && code !== 201) {
    throw new Error('Jira API error ' + code + ': ' + response.getContentText());
  }

  return JSON.parse(response.getContentText());
}

function updateSheetSummary(trackName, summary) {
  var sheet = SpreadsheetApp.getActiveSheet();
  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  var commentsCol = headers.indexOf('Comments') + 1;

  if (commentsCol < 1) throw new Error('No "Comments" column found.');

  var data = sheet.getRange(2, 1, sheet.getLastRow() - 1, sheet.getLastColumn()).getValues();
  for (var r = 0; r < data.length; r++) {
    var rd = {};
    for (var c = 0; c < headers.length; c++) {
      rd[headers[c]] = (data[r][c] || '').toString().trim();
    }
    if (rd['WorkType'] === 'Track' && rd['Description'].toLowerCase() === trackName.toLowerCase()) {
      sheet.getRange(r + 2, commentsCol).setValue(summary);
      return;
    }
  }
}

// --------------- Google Docs helper ---------------

function getDocText(urlOrId) {
  var match = urlOrId.match(/\/document\/d\/([a-zA-Z0-9_-]+)/);
  var docId = match ? match[1] : urlOrId.trim();
  var doc = DocumentApp.openById(docId);
  return doc.getBody().getText();
}
