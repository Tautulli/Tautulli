const assert = require('assert');
const Module = require('module');

const NOW = 1_800_000_000_000;
const DAY = 24 * 60 * 60 * 1000;
const DEFAULT_CYCLE_ID = 'audit-00000000000000000000000000000001';
const MEMBER = {id: 'user-1', login: 'member'};
const OTHER_MEMBER = {id: 'user-2', login: 'other-member'};

const runtime = {
  matches: {},
  reporters: {},
  created: [],
  searchCalls: [],
  mutations: [],
  globalMutations: [],
  effects: [],
  globalStorage: null,
  now: NOW,
  failOnField: null
};

function trackedFields(issueId, initial) {
  return new Proxy(Object.assign({}, initial || {}), {
    set: function(target, fieldName, value) {
      runtime.mutations.push({issueId: issueId, fieldName: String(fieldName), value: value});
      runtime.effects.push({type: 'issue', fieldName: String(fieldName)});
      if (runtime.failOnField === fieldName) {
        throw new Error('simulated mutation failure for ' + fieldName);
      }
      target[fieldName] = value;
      return true;
    }
  });
}

function trackedGlobalStorage(initial) {
  return new Proxy(Object.assign({}, initial || {}), {
    set: function(target, propertyName, value) {
      runtime.globalMutations.push({propertyName: String(propertyName), value: value});
      runtime.effects.push({type: 'global', propertyName: String(propertyName)});
      target[propertyName] = value;
      return true;
    }
  });
}

function MockIssue(reporter, project, summary) {
  const issueId = 'CMA-NEW-' + (runtime.created.length + 1);
  runtime.effects.push({type: 'issue-create', issueId: issueId});
  const issue = {
    id: issueId,
    reporter: reporter,
    project: project,
    summary: summary,
    description: '',
    fields: trackedFields(issueId)
  };
  runtime.created.push(issue);
  return issue;
}

const originalLoad = Module._load;
Module._load = function(request, parent, isMain) {
  if (request === '@jetbrains/youtrack-scripting-api/entities') {
    return {
      Issue: MockIssue,
      User: {
        findUniqueByEmail: function(email) {
          return runtime.reporters[email] || null;
        },
        fieldType: {}
      },
      Field: {
        stringType: {},
        dateType: {},
        dateTimeType: {},
        integerType: {}
      },
      EnumField: {fieldType: {}}
    };
  }
  if (request === '@jetbrains/youtrack-scripting-api/search') {
    return {
      search: function(project, query) {
        runtime.searchCalls.push(query.query);
        const field = query.query.indexOf('{Plex User ID}:') === 0 ?
          'Plex User ID' : 'Plex Username';
        return runtime.matches[field] || [];
      }
    };
  }
  return originalLoad(request, parent, isMain);
};

const endpointDefinitions = require('../account-sync').httpHandler.endpoints;
const syncEndpoint = endpointDefinitions.find(function(endpoint) {
  return endpoint.path === 'sync-account' && endpoint.method === 'POST';
});
const protocolEndpoint = endpointDefinitions.find(function(endpoint) {
  return endpoint.path === 'protocol' && endpoint.method === 'GET';
});
assert.ok(syncEndpoint, 'sync-account POST endpoint is missing');
assert.ok(protocolEndpoint, 'protocol GET endpoint is missing');
const handler = syncEndpoint.handle;
const protocolHandler = protocolEndpoint.handle;
Module._load = originalLoad;

const bundles = {
  'Account Status': ['Active', 'Inactive', 'Never Used'],
  State: ['New', 'Open', 'Pending', 'Solved'],
  'Review Stage': [
    'Active',
    'Inactivity Notice',
    'Subject to Deletion',
    'Final Reminder',
    'Removal Due',
    'Access Removed',
    'Access Retained',
    'Exempt'
  ]
};

const scalarFields = [
  'Plex User ID',
  'Plex Username',
  'Last Streamed',
  'Total Plays',
  'Watch Time',
  'Account Audit Confirmed At'
];

function resetRuntime() {
  runtime.matches = {};
  runtime.reporters = {};
  runtime.created = [];
  runtime.searchCalls = [];
  runtime.mutations = [];
  runtime.globalMutations = [];
  runtime.effects = [];
  runtime.globalStorage = trackedGlobalStorage();
  runtime.now = NOW;
  runtime.failOnField = null;
}

function seedGlobalBudget(reservedAt) {
  runtime.globalStorage.cmaMemberNotificationReservedAt = reservedAt;
  runtime.globalStorage.cmaMemberNotificationCycleId = DEFAULT_CYCLE_ID;
  runtime.globalStorage.cmaMemberNotificationPlexUserId = 'plex-previous';
  runtime.globalMutations = [];
  runtime.effects = [];
}

function project(shortName, options) {
  options = options || {};
  const missingFields = options.missingFields || [];
  const missingValues = options.missingValues || {};
  const projectFields = {};

  scalarFields.forEach(function(fieldName) {
    projectFields[fieldName] = {};
  });
  Object.keys(bundles).forEach(function(fieldName) {
    const values = {};
    bundles[fieldName].forEach(function(name) {
      if ((missingValues[fieldName] || []).indexOf(name) === -1) {
        values[name] = {name: name};
      }
    });
    projectFields[fieldName] = {
      findValueByName: function(name) { return values[name] || null; }
    };
  });
  missingFields.forEach(function(fieldName) {
    delete projectFields[fieldName];
  });

  return {
    shortName: shortName || 'CMA',
    findFieldByName: function(name) { return projectFields[name] || null; },
    value: function(fieldName, valueName) {
      const field = projectFields[fieldName];
      return field && field.findValueByName ? field.findValueByName(valueName) : null;
    }
  };
}

function validBody(overrides) {
  return Object.assign({
    plexUserId: 'plex-123',
    plexUsername: 'member',
    totalPlays: 12,
    watchSeconds: 3600,
    lastStreamedMs: NOW - (60 * 24 * 60 * 60 * 1000),
    watchTime: '1 hrs 0 mins',
    accountStatus: 'Inactive',
    reviewNeeded: true,
    onboardingRequested: false,
    email: 'member@example.com',
    notificationMode: 'permit',
    cycleId: DEFAULT_CYCLE_ID
  }, overrides || {});
}

function context(body, projectOverride) {
  const response = {
    code: 200,
    payload: null,
    json: function(value) { this.payload = value; }
  };
  return {
    project: projectOverride || project('CMA'),
    currentUser: {login: 'audit-bot'},
    globalStorage: {extensionProperties: runtime.globalStorage},
    request: {json: function() { return body; }},
    response: response
  };
}

function existingIssue(targetProject, options) {
  options = options || {};
  const issueId = options.id || 'CMA-2';
  const initial = {
    'Plex User ID': options.plexUserId || 'plex-123',
    'Plex Username': options.plexUsername || 'member',
    'Account Status': targetProject.value(
      'Account Status',
      options.accountStatus || 'Inactive'
    ),
    'Review Stage': options.stage ? targetProject.value('Review Stage', options.stage) : null
  };
  if (options.confirmedAt !== undefined) {
    initial['Account Audit Confirmed At'] = options.confirmedAt;
  }
  return {
    id: issueId,
    project: targetProject,
    reporter: options.reporter === undefined ? MEMBER : options.reporter,
    fields: trackedFields(issueId, initial)
  };
}

function matchExisting(issue) {
  runtime.matches['Plex User ID'] = [issue];
  runtime.reporters['member@example.com'] = MEMBER;
}

function assertNoMutation() {
  assert.deepStrictEqual(runtime.mutations, []);
  assert.deepStrictEqual(runtime.globalMutations, []);
  assert.strictEqual(runtime.created.length, 0);
}

function assertReceipt(payload, expected) {
  assert.strictEqual(payload.notificationPolicyVersion, 2);
  assert.strictEqual(payload.notificationMode, expected.mode);
  assert.strictEqual(payload.cycleId, expected.cycleId || DEFAULT_CYCLE_ID);
  assert.strictEqual(
    payload.memberNotificationPermitRequired,
    expected.required
  );
  assert.strictEqual(
    payload.memberNotificationPermitReserved,
    expected.reserved
  );
  assert.strictEqual(
    payload.memberNotificationBudgetRemaining,
    expected.remaining
  );
  assert.strictEqual(payload.plexUserId, expected.plexUserId || 'plex-123');
  assert.strictEqual(
    payload.onboardingRequested,
    expected.onboardingRequested || false
  );
  assert.strictEqual(
    payload.onboardingCompleted,
    expected.onboardingCompleted || false
  );
}

function testProjectBoundary() {
  resetRuntime();
  const ctx = context(validBody(), project('SUPPORT'));
  handler(ctx);
  assert.strictEqual(ctx.response.code, 403);
  assert.strictEqual(runtime.searchCalls.length, 0);
  assertNoMutation();
}

function testPayloadValidationStopsBeforeSearchOrMutation() {
  const invalidPayloads = [
    {body: null, error: /JSON object/},
    {body: validBody({plexUserId: ''}), error: /plexUserId/},
    {body: validBody({email: ''}), error: /email/},
    {body: validBody({onboardingRequested: 'yes'}), error: /onboardingRequested/},
    {body: validBody({notificationMode: undefined}), error: /notificationMode/},
    {body: validBody({notificationMode: 'preview'}), error: /notificationMode/},
    {body: validBody({notificationMode: ' permit '}), error: /notificationMode/},
    {body: validBody({cycleId: undefined}), error: /cycleId/},
    {body: validBody({cycleId: 'audit-ABC'}), error: /cycleId/},
    {body: validBody({cycleId: ' ' + DEFAULT_CYCLE_ID}), error: /cycleId/},
    {
      body: validBody({cycleId: 'audit-000000000000000000000000000000001'}),
      error: /cycleId/
    },
    {body: validBody({totalPlays: Number.MAX_SAFE_INTEGER + 1}), error: /safe integer/},
    {body: validBody({watchSeconds: 1.5}), error: /safe integer/},
    {body: validBody({watchTime: '999 hrs'}), error: /watchTime does not match/},
    {body: validBody({accountStatus: 'Paused'}), error: /accountStatus/},
    {body: validBody({accountStatus: 'Never Used'}), error: /Never Used requires/},
    {
      body: validBody({accountStatus: 'Inactive', totalPlays: 0, lastStreamedMs: null}),
      error: /Never Used requires/
    },
    {body: validBody({totalPlays: 0}), error: /zero-play accounts/},
    {body: validBody({lastStreamedMs: null}), error: /accounts with plays/},
    {
      body: validBody({accountStatus: 'Active', reviewNeeded: true}),
      error: /Active requires/
    },
    {
      body: validBody({accountStatus: 'Inactive', reviewNeeded: false}),
      error: /Inactive requires/
    },
    {body: validBody({lastStreamedMs: 0}), error: /positive timestamp/},
    {
      body: validBody({lastStreamedMs: NOW + (5 * 60 * 1000) + 1}),
      error: /future/
    }
  ];

  invalidPayloads.forEach(function(entry) {
    resetRuntime();
    const ctx = context(entry.body);
    handler(ctx);
    assert.strictEqual(ctx.response.code, 400);
    assert.match(ctx.response.payload.error, entry.error);
    assert.strictEqual(runtime.searchCalls.length, 0);
    assertNoMutation();
  });
}

function testFutureTimestampAtSkewBoundaryIsAccepted() {
  resetRuntime();
  const ctx = context(validBody({
    accountStatus: 'Active',
    reviewNeeded: false,
    lastStreamedMs: NOW + (5 * 60 * 1000)
  }));
  handler(ctx);
  assert.strictEqual(ctx.response.payload.result, 'planned');
  assertNoMutation();
}

function testHealthyAccountDoesNotCreateOrStampATicket() {
  resetRuntime();
  const ctx = context(validBody({accountStatus: 'Active', reviewNeeded: false}));
  handler(ctx);
  assert.strictEqual(ctx.response.payload.result, 'planned');
  assert.strictEqual(ctx.response.payload.action, 'facts-only');
  assert.strictEqual(ctx.response.payload.plannedAction, 'facts-only');
  assert.strictEqual(ctx.response.payload.reviewStage, null);
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    required: false,
    reserved: false,
    remaining: 15
  });
  assertNoMutation();
}

function testProtocolEndpointIsExactReadOnlyAndCmaScoped() {
  resetRuntime();
  let ctx = context(null);
  protocolHandler(ctx);
  assert.strictEqual(ctx.response.code, 200);
  assert.deepStrictEqual(ctx.response.payload, {
    appName: 'cma-account-audit-member-notification',
    notificationPolicyVersion: 2,
    notificationModes: ['suppress', 'permit'],
    memberNotificationLimit: 15,
    memberNotificationWindowSeconds: 24 * 60 * 60,
    onboardingProtocolVersion: 1
  });
  assert.strictEqual(runtime.searchCalls.length, 0);
  assertNoMutation();

  resetRuntime();
  ctx = context(null, project('SUPPORT'));
  protocolHandler(ctx);
  assert.strictEqual(ctx.response.code, 403);
  assert.strictEqual(runtime.searchCalls.length, 0);
  assertNoMutation();

  resetRuntime();
  seedGlobalBudget(NOW + 1);
  ctx = context(null);
  protocolHandler(ctx);
  assert.strictEqual(ctx.response.code, 503);
  assert.match(ctx.response.payload.error, /budget timestamp/);
  assert.strictEqual(runtime.searchCalls.length, 0);
  assertNoMutation();
}

function testCanonicalNeverUsedFactsAreAccepted() {
  resetRuntime();
  let ctx = context(validBody({
    totalPlays: 0,
    lastStreamedMs: null,
    watchSeconds: 0,
    watchTime: '0 mins',
    accountStatus: 'Never Used',
    reviewNeeded: false
  }));
  handler(ctx);
  assert.strictEqual(ctx.response.payload.result, 'planned');
  assertNoMutation();

  resetRuntime();
  runtime.reporters['member@example.com'] = MEMBER;
  ctx = context(validBody({
    totalPlays: 0,
    lastStreamedMs: null,
    watchSeconds: 0,
    watchTime: '0 mins',
    accountStatus: 'Never Used',
    reviewNeeded: true
  }));
  handler(ctx);
  assert.strictEqual(ctx.response.payload.result, 'created');
  assert.strictEqual(ctx.response.payload.action, 'ticket-created-awaiting-notice');
  assert.strictEqual(runtime.created[0].fields['Account Status'].name, 'Never Used');
  assert.strictEqual(runtime.created[0].fields['Review Stage'].name, 'Active');
  assert.strictEqual(runtime.created[0].fields['Account Audit Confirmed At'], undefined);
}

function testNewReviewRequiresAReporterBeforeCreation() {
  resetRuntime();
  const ctx = context(validBody());
  handler(ctx);
  assert.strictEqual(ctx.response.code, 422);
  assert.match(ctx.response.payload.error, /reporter/);
  assertNoMutation();
}

function testNewReviewCreationAndFirstNoticeUseSeparatePermits() {
  resetRuntime();
  runtime.reporters['member@example.com'] = MEMBER;
  let ctx = context(validBody());
  handler(ctx);
  assert.strictEqual(ctx.response.payload.result, 'created');
  assert.strictEqual(ctx.response.payload.action, 'ticket-created-awaiting-notice');
  assert.strictEqual(
    ctx.response.payload.plannedAction,
    'ticket-created-awaiting-notice'
  );
  assert.strictEqual(runtime.created.length, 1);
  assert.strictEqual(runtime.created[0].fields['Review Stage'].name, 'Active');
  assert.strictEqual(runtime.created[0].fields['Plex User ID'], 'plex-123');
  assert.strictEqual(runtime.created[0].fields['Account Audit Confirmed At'], undefined);
  assert.strictEqual(
    runtime.mutations.filter(function(item) {
      return item.fieldName === 'Account Audit Confirmed At';
    }).length,
    0
  );
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    required: true,
    reserved: true,
    remaining: 14
  });

  const created = runtime.created[0];
  runtime.now += DAY;
  matchExisting(created);
  runtime.mutations = [];
  runtime.globalMutations = [];
  runtime.effects = [];
  ctx = context(validBody({
    cycleId: 'audit-00000000000000000000000000000002'
  }), created.project);
  handler(ctx);

  assert.strictEqual(ctx.response.payload.result, 'updated');
  assert.strictEqual(ctx.response.payload.action, 'notice-started');
  assert.strictEqual(ctx.response.payload.plannedAction, 'notice-started');
  assert.strictEqual(created.fields['Review Stage'].name, 'Inactivity Notice');
  assert.strictEqual(created.fields['Account Audit Confirmed At'], runtime.now);
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    cycleId: 'audit-00000000000000000000000000000002',
    required: true,
    reserved: true,
    remaining: 14
  });
}

function testDuplicateAndCrossIdentifierConflictsDoNotMutate() {
  resetRuntime();
  let targetProject = project('CMA');
  runtime.matches['Plex User ID'] = [
    existingIssue(targetProject, {id: 'CMA-2'}),
    existingIssue(targetProject, {id: 'CMA-3'})
  ];
  let ctx = context(validBody(), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.code, 409);
  assert.match(ctx.response.payload.error, /Multiple CMA tickets/);
  assertNoMutation();

  resetRuntime();
  targetProject = project('CMA');
  runtime.matches['Plex User ID'] = [
    existingIssue(targetProject, {id: 'CMA-2', plexUsername: 'member-old'})
  ];
  runtime.matches['Plex Username'] = [
    existingIssue(targetProject, {id: 'CMA-3', plexUserId: 'plex-other'})
  ];
  ctx = context(validBody(), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.code, 409);
  assert.match(ctx.response.payload.error, /different CMA tickets/);
  assertNoMutation();

  resetRuntime();
  targetProject = project('CMA');
  runtime.matches['Plex Username'] = [
    existingIssue(targetProject, {id: 'CMA-4', plexUserId: 'plex-other'})
  ];
  ctx = context(validBody(), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.code, 409);
  assert.match(ctx.response.payload.error, /different Plex User ID/);
  assertNoMutation();
}

function testExistingReporterMustResolveAndMatchBeforeMutation() {
  resetRuntime();
  let targetProject = project('CMA');
  let existing = existingIssue(targetProject, {confirmedAt: 123});
  runtime.matches['Plex User ID'] = [existing];
  let ctx = context(validBody(), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.code, 422);
  assert.match(ctx.response.payload.error, /reporter/);
  assert.strictEqual(existing.fields['Account Audit Confirmed At'], 123);
  assertNoMutation();

  resetRuntime();
  targetProject = project('CMA');
  existing = existingIssue(targetProject, {confirmedAt: 123});
  runtime.matches['Plex User ID'] = [existing];
  runtime.reporters['member@example.com'] = OTHER_MEMBER;
  ctx = context(validBody(), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.code, 409);
  assert.match(ctx.response.payload.error, /reporter does not match/);
  assert.strictEqual(existing.fields['Account Audit Confirmed At'], 123);
  assertNoMutation();
}

function testAuditCallerMustDifferFromReporter() {
  resetRuntime();
  runtime.reporters['member@example.com'] = MEMBER;
  let ctx = context(validBody());
  ctx.currentUser = MEMBER;
  handler(ctx);

  assert.strictEqual(ctx.response.code, 403);
  assert.match(ctx.response.payload.error, /caller cannot be the ticket reporter/);
  assertNoMutation();

  resetRuntime();
  runtime.reporters['member@example.com'] = MEMBER;
  ctx = context(validBody());
  ctx.currentUser = {id: 'audit-user-1', login: 'audit-bot'};
  handler(ctx);

  assert.strictEqual(ctx.response.payload.result, 'created');
  assert.strictEqual(ctx.response.payload.action, 'ticket-created-awaiting-notice');
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    required: true,
    reserved: true,
    remaining: 14
  });
  assert.strictEqual(runtime.created.length, 1);
}

function testMissingFieldsAndBundleValuesFailBeforeMutation() {
  resetRuntime();
  let targetProject = project('CMA', {missingFields: ['Account Audit Confirmed At']});
  let existing = existingIssue(targetProject);
  matchExisting(existing);
  let ctx = context(validBody(), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.code, 422);
  assert.match(ctx.response.payload.error, /Account Audit Confirmed At/);
  assertNoMutation();

  resetRuntime();
  targetProject = project('CMA', {missingValues: {'Account Status': ['Inactive']}});
  existing = existingIssue(targetProject, {accountStatus: 'Active'});
  matchExisting(existing);
  ctx = context(validBody(), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.code, 422);
  assert.match(ctx.response.payload.error, /Account Status does not contain value Inactive/);
  assertNoMutation();

  resetRuntime();
  targetProject = project('CMA', {missingValues: {'Review Stage': ['Inactivity Notice']}});
  existing = existingIssue(targetProject);
  matchExisting(existing);
  ctx = context(validBody(), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.code, 422);
  assert.match(ctx.response.payload.error, /Review Stage does not contain value Inactivity Notice/);
  assertNoMutation();
}

function testSuccessfulExistingUpdateChangesFactsAndExactStamp() {
  resetRuntime();
  const targetProject = project('CMA');
  const existing = existingIssue(targetProject, {confirmedAt: 123});
  matchExisting(existing);
  const ctx = context(validBody(), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.payload.result, 'updated');
  assert.strictEqual(ctx.response.payload.action, 'notice-started');
  assert.strictEqual(existing.fields['Review Stage'].name, 'Inactivity Notice');
  assert.strictEqual(existing.fields['Total Plays'], 12);
  assert.strictEqual(existing.fields['Account Audit Confirmed At'], runtime.now);
}

function testMutationExceptionEscapesAndCannotStampSuccess() {
  resetRuntime();
  const targetProject = project('CMA');
  const existing = existingIssue(targetProject, {confirmedAt: 123});
  matchExisting(existing);
  runtime.failOnField = 'Review Stage';
  const ctx = context(validBody(), targetProject);
  assert.throws(function() { handler(ctx); }, /simulated mutation failure/);
  assert.strictEqual(ctx.response.payload, null);
  assert.strictEqual(existing.fields['Account Audit Confirmed At'], 123);
  assert.strictEqual(
    runtime.mutations.some(function(item) {
      return item.fieldName === 'Account Audit Confirmed At';
    }),
    false
  );
}

function testRepeatedDailySyncDoesNotRestartAnOpenReview() {
  resetRuntime();
  const targetProject = project('CMA');
  const existing = existingIssue(targetProject, {stage: 'Inactivity Notice'});
  matchExisting(existing);

  const first = context(validBody(), targetProject);
  handler(first);
  runtime.now += DAY;
  const second = context(validBody({
    cycleId: 'audit-00000000000000000000000000000002'
  }), targetProject);
  handler(second);

  assert.strictEqual(first.response.payload.action, 'review-already-in-progress');
  assert.strictEqual(second.response.payload.action, 'review-already-in-progress');
  assert.strictEqual(existing.fields['Review Stage'].name, 'Inactivity Notice');
  assert.strictEqual(runtime.created.length, 0);
  assert.strictEqual(existing.fields['Account Audit Confirmed At'], runtime.now);
}

function testActivityAutomaticallyRetainsAnOpenReview() {
  resetRuntime();
  const targetProject = project('CMA');
  const existing = existingIssue(targetProject, {stage: 'Subject to Deletion'});
  matchExisting(existing);
  const ctx = context(validBody({accountStatus: 'Active', reviewNeeded: false}), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.payload.action, 'retained');
  assert.strictEqual(existing.fields['Review Stage'].name, 'Access Retained');
  assert.strictEqual(existing.fields['Account Audit Confirmed At'], NOW);
}

function testActivityRetainsAStagedTicketBeforeItsFirstNotice() {
  resetRuntime();
  const targetProject = project('CMA');
  const existing = existingIssue(targetProject, {
    stage: 'Active',
    accountStatus: 'Inactive'
  });
  matchExisting(existing);

  let ctx = context(validBody({
    accountStatus: 'Active',
    reviewNeeded: false,
    notificationMode: 'suppress'
  }), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.payload.result, 'deferred');
  assert.strictEqual(ctx.response.payload.plannedAction, 'retained');
  assertReceipt(ctx.response.payload, {
    mode: 'suppress',
    required: true,
    reserved: false,
    remaining: 15
  });
  assert.strictEqual(existing.fields['Review Stage'].name, 'Active');
  assert.strictEqual(existing.fields['Account Status'].name, 'Inactive');
  assertNoMutation();

  ctx = context(validBody({
    accountStatus: 'Active',
    reviewNeeded: false
  }), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.payload.result, 'updated');
  assert.strictEqual(ctx.response.payload.action, 'retained');
  assert.strictEqual(existing.fields['Review Stage'].name, 'Access Retained');
  assert.strictEqual(existing.fields['Account Status'].name, 'Active');
  assert.strictEqual(existing.fields['Account Audit Confirmed At'], NOW);
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    required: true,
    reserved: true,
    remaining: 14
  });
}

function testFirstEverStreamByANewMemberDoesNotCloseAReviewThatNeverOpened() {
  // OPS-496. A newly onboarded member sits at Review Stage 'Active' with
  // Account Status 'Never Used' - the same shape as a review ticket awaiting
  // its first notice. When they stream for the first time they must NOT be
  // told a review was closed: no review was ever opened and no notice was ever
  // sent. The staged-review case (previous status 'Inactive') is covered by
  // testActivityRetainsAStagedTicketBeforeItsFirstNotice and is unaffected.
  resetRuntime();
  const targetProject = project('CMA');
  const existing = existingIssue(targetProject, {
    stage: 'Active',
    accountStatus: 'Never Used',
    confirmedAt: 123
  });
  matchExisting(existing);

  const ctx = context(validBody({
    accountStatus: 'Active',
    reviewNeeded: false
  }), targetProject);
  handler(ctx);

  assert.strictEqual(ctx.response.payload.result, 'planned');
  assert.strictEqual(ctx.response.payload.action, 'facts-only');
  assert.strictEqual(existing.fields['Review Stage'].name, 'Active');
  assert.strictEqual(existing.fields['Account Status'].name, 'Never Used');
  assert.strictEqual(existing.fields['Account Audit Confirmed At'], 123);
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    required: false,
    reserved: false,
    remaining: 15
  });
  assertNoMutation();
}

function testRetainedReviewNeedsANewActiveBaselineBeforeRestart() {
  resetRuntime();
  const targetProject = project('CMA');
  const existing = existingIssue(targetProject, {
    stage: 'Access Retained',
    accountStatus: 'Inactive'
  });
  matchExisting(existing);

  let ctx = context(validBody(), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.payload.action, 'retained-awaiting-new-active-baseline');
  assert.strictEqual(existing.fields['Review Stage'].name, 'Access Retained');

  runtime.now += DAY;
  ctx = context(validBody({
    accountStatus: 'Active',
    reviewNeeded: false,
    cycleId: 'audit-00000000000000000000000000000002'
  }), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.payload.action, 'facts-only');
  assert.strictEqual(existing.fields['Account Status'].name, 'Active');

  runtime.now += DAY;
  ctx = context(validBody({
    accountStatus: 'Inactive',
    reviewNeeded: true,
    cycleId: 'audit-00000000000000000000000000000003'
  }), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.payload.action, 'notice-restarted-after-active-baseline');
  assert.strictEqual(existing.fields['Review Stage'].name, 'Inactivity Notice');
}

function testPermitModeNonCandidateIsCompletelyReadOnly() {
  resetRuntime();
  const targetProject = project('CMA');
  const existing = existingIssue(targetProject, {stage: 'Exempt', confirmedAt: 123});
  matchExisting(existing);
  const ctx = context(validBody(), targetProject);
  handler(ctx);
  assert.strictEqual(ctx.response.payload.result, 'planned');
  assert.strictEqual(ctx.response.payload.action, 'protected-terminal-stage');
  assert.strictEqual(existing.fields['Review Stage'].name, 'Exempt');
  assert.strictEqual(existing.fields['Account Audit Confirmed At'], 123);
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    required: false,
    reserved: false,
    remaining: 15
  });
  assertNoMutation();
}

function testSuppressDefersNewCandidateWithoutAnyMutation() {
  resetRuntime();
  runtime.reporters['member@example.com'] = MEMBER;
  const ctx = context(validBody({notificationMode: 'suppress'}));
  handler(ctx);

  assert.strictEqual(ctx.response.payload.result, 'deferred');
  assert.strictEqual(ctx.response.payload.action, 'member-notification-deferred');
  assert.strictEqual(
    ctx.response.payload.plannedAction,
    'ticket-created-awaiting-notice'
  );
  assert.strictEqual(ctx.response.payload.issueId, null);
  assert.strictEqual(ctx.response.payload.reviewStage, null);
  assertReceipt(ctx.response.payload, {
    mode: 'suppress',
    required: true,
    reserved: false,
    remaining: 15
  });
  assertNoMutation();
}

function testSuppressConservativelyDefersEveryMessageStage() {
  [
    'Inactivity Notice',
    'Subject to Deletion',
    'Final Reminder',
    'Access Removed',
    'Access Retained'
  ].forEach(function(stage) {
    resetRuntime();
    const targetProject = project('CMA');
    const existing = existingIssue(targetProject, {stage: stage, confirmedAt: 123});
    matchExisting(existing);
    const ctx = context(validBody({notificationMode: 'suppress'}), targetProject);
    handler(ctx);

    assert.strictEqual(ctx.response.payload.result, 'deferred', stage);
    assert.strictEqual(
      ctx.response.payload.action,
      'member-notification-deferred',
      stage
    );
    assert.strictEqual(ctx.response.payload.reviewStage, stage);
    assert.strictEqual(existing.fields['Account Audit Confirmed At'], 123);
    assertReceipt(ctx.response.payload, {
      mode: 'suppress',
      required: true,
      reserved: false,
      remaining: 15
    });
    assertNoMutation();
  });
}

function testSuppressPlansSafeExistingFactsWithoutMutation() {
  ['Exempt', 'Removal Due'].forEach(function(stage) {
    resetRuntime();
    const targetProject = project('CMA');
    const existing = existingIssue(targetProject, {stage: stage, confirmedAt: 123});
    matchExisting(existing);
    const ctx = context(validBody({notificationMode: 'suppress'}), targetProject);
    handler(ctx);

    assert.strictEqual(ctx.response.payload.result, 'planned', stage);
    assert.strictEqual(ctx.response.payload.reviewStage, stage);
    assert.strictEqual(existing.fields['Review Stage'].name, stage);
    assert.strictEqual(existing.fields['Account Audit Confirmed At'], 123);
    assertReceipt(ctx.response.payload, {
      mode: 'suppress',
      required: false,
      reserved: false,
      remaining: 15
    });
    assertNoMutation();
  });
}

function testPermitReservesIntoArrayStorageAndTracksMultipleSlots() {
  resetRuntime();
  runtime.reporters['member@example.com'] = MEMBER;
  let ctx = context(validBody());
  handler(ctx);

  assert.strictEqual(ctx.response.payload.result, 'created');
  assert.strictEqual(ctx.response.payload.action, 'ticket-created-awaiting-notice');
  assert.strictEqual(
    ctx.response.payload.plannedAction,
    'ticket-created-awaiting-notice'
  );
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    required: true,
    reserved: true,
    remaining: 14
  });
  // The legacy single-slot fields are never written by this version.
  assert.strictEqual(runtime.globalStorage.cmaMemberNotificationReservedAt, undefined);
  assert.strictEqual(runtime.globalStorage.cmaMemberNotificationCycleId, undefined);
  assert.strictEqual(runtime.globalStorage.cmaMemberNotificationPlexUserId, undefined);
  assert.deepStrictEqual(
    JSON.parse(runtime.globalStorage.cmaMemberNotificationReservations),
    [{reservedAt: NOW, cycleId: DEFAULT_CYCLE_ID, plexUserId: 'plex-123'}]
  );
  // One JSON-array write replaces the three separate scalar writes the
  // single-slot policy used to make, and it still happens before any issue
  // side effect.
  assert.deepStrictEqual(
    runtime.effects.slice(0, 2).map(function(effect) { return effect.type; }),
    ['global', 'issue-create']
  );

  const targetProject = project('CMA');
  const second = existingIssue(targetProject, {
    id: 'CMA-3',
    stage: 'Final Reminder',
    confirmedAt: 123
  });
  runtime.matches = {};
  runtime.reporters = {};
  matchExisting(second);
  runtime.created = [];
  runtime.mutations = [];
  runtime.globalMutations = [];
  runtime.effects = [];
  ctx = context(validBody({
    cycleId: 'audit-00000000000000000000000000000002'
  }), targetProject);
  handler(ctx);

  // A second concurrent member is still well inside the 15-slot ceiling, so
  // this permit succeeds instead of deferring.
  assert.strictEqual(ctx.response.payload.result, 'updated');
  assert.strictEqual(ctx.response.payload.action, 'review-already-in-progress');
  assert.strictEqual(second.fields['Account Audit Confirmed At'], runtime.now);
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    cycleId: 'audit-00000000000000000000000000000002',
    required: true,
    reserved: true,
    remaining: 13
  });
  assert.strictEqual(
    JSON.parse(runtime.globalStorage.cmaMemberNotificationReservations).length,
    2
  );
}

function testFifteenConcurrentReservationsFillTheCeilingAndTheSixteenthIsBlocked() {
  resetRuntime();
  const targetProject = project('CMA');
  const preExisting = [];
  for (let i = 0; i < 14; i += 1) {
    preExisting.push({
      reservedAt: NOW - (i * 1000),
      cycleId: 'audit-' + String(i).padStart(32, '0'),
      plexUserId: 'plex-seed-' + i
    });
  }
  runtime.globalStorage.cmaMemberNotificationReservations = JSON.stringify(preExisting);

  runtime.reporters['member@example.com'] = MEMBER;
  let ctx = context(validBody(), targetProject);
  handler(ctx);

  // The 15th concurrent reservation is still permitted; it exactly fills
  // the ceiling advertised by the protocol endpoint.
  assert.strictEqual(ctx.response.payload.result, 'created');
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    required: true,
    reserved: true,
    remaining: 0
  });
  assert.strictEqual(
    JSON.parse(runtime.globalStorage.cmaMemberNotificationReservations).length,
    15
  );

  const blocked = existingIssue(targetProject, {
    id: 'CMA-16',
    stage: 'Final Reminder',
    confirmedAt: 123
  });
  runtime.matches = {};
  runtime.reporters = {};
  matchExisting(blocked);
  runtime.created = [];
  runtime.mutations = [];
  runtime.globalMutations = [];
  runtime.effects = [];
  ctx = context(validBody({
    cycleId: 'audit-00000000000000000000000000000099'
  }), targetProject);
  handler(ctx);

  assert.strictEqual(ctx.response.payload.result, 'deferred');
  assert.strictEqual(
    ctx.response.payload.action,
    'member-notification-budget-exhausted'
  );
  assert.strictEqual(ctx.response.payload.plannedAction, 'review-already-in-progress');
  assert.strictEqual(blocked.fields['Account Audit Confirmed At'], 123);
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    cycleId: 'audit-00000000000000000000000000000099',
    required: true,
    reserved: false,
    remaining: 0
  });
  assertNoMutation();
}

function testEachReservationExpiresIndependentlyOnItsOwnRollingWindow() {
  resetRuntime();
  const targetProject = project('CMA');
  const seeded = [];
  for (let i = 0; i < 15; i += 1) {
    seeded.push({
      // 5 slots are already more than 24 hours old; the other 10 are fresh.
      // Each must age out on its own timestamp, not as a group.
      reservedAt: i < 5 ? NOW - DAY - 1000 : NOW - 1000,
      cycleId: 'audit-' + String(i).padStart(32, '0'),
      plexUserId: 'plex-seed-' + i
    });
  }
  runtime.globalStorage.cmaMemberNotificationReservations = JSON.stringify(seeded);
  runtime.globalMutations = [];
  runtime.effects = [];

  let ctx = context(null, targetProject);
  protocolHandler(ctx);
  assert.strictEqual(ctx.response.code, 200);
  assertNoMutation();

  runtime.reporters['member@example.com'] = MEMBER;
  ctx = context(validBody(), targetProject);
  handler(ctx);

  assert.strictEqual(ctx.response.payload.result, 'created');
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    required: true,
    reserved: true,
    remaining: 4
  });
  const stored = JSON.parse(runtime.globalStorage.cmaMemberNotificationReservations);
  // The 5 stale entries are dropped on write; only the 10 still-active ones
  // plus the new reservation remain.
  assert.strictEqual(stored.length, 11);
  assert.ok(stored.every(function(entry) { return entry.reservedAt > NOW - DAY; }));
}

function testLegacyReservationMigratesIntoArrayExactlyOnceWithoutLossOrDuplication() {
  resetRuntime();
  seedGlobalBudget(NOW - DAY + 1000);

  // Before this version has written anything, the legacy single-slot fields
  // are still the sole record of a possibly-live reservation and must be
  // honored, not silently dropped or reopened.
  let ctx = context(null);
  protocolHandler(ctx);
  assert.strictEqual(ctx.response.code, 200);
  assert.strictEqual(runtime.globalStorage.cmaMemberNotificationReservations, undefined);

  runtime.reporters['second-member@example.com'] = OTHER_MEMBER;
  ctx = context(validBody({
    plexUserId: 'plex-456',
    plexUsername: 'other-member',
    email: 'second-member@example.com',
    cycleId: 'audit-00000000000000000000000000000009'
  }));
  handler(ctx);

  assert.strictEqual(ctx.response.payload.result, 'created');
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    cycleId: 'audit-00000000000000000000000000000009',
    required: true,
    reserved: true,
    remaining: 13,
    plexUserId: 'plex-456'
  });

  const migrated = JSON.parse(runtime.globalStorage.cmaMemberNotificationReservations);
  assert.strictEqual(migrated.length, 2);
  assert.deepStrictEqual(migrated[0], {
    reservedAt: NOW - DAY + 1000,
    cycleId: DEFAULT_CYCLE_ID,
    plexUserId: 'plex-previous'
  });
  assert.strictEqual(migrated[1].plexUserId, 'plex-456');

  // Once the array exists it is authoritative: corrupting the now-inert
  // legacy fields must not fail-close a budget read that no longer uses them.
  runtime.globalStorage.cmaMemberNotificationCycleId = 'not-a-cycle-id';
  ctx = context(null);
  protocolHandler(ctx);
  assert.strictEqual(ctx.response.code, 200);
}

function testMalformedReservationArrayFailsClosed() {
  const invalidPayloads = [
    'not-json',
    JSON.stringify({not: 'an-array'}),
    JSON.stringify([{reservedAt: -1, cycleId: DEFAULT_CYCLE_ID, plexUserId: 'plex-x'}]),
    JSON.stringify([{reservedAt: NOW + 1, cycleId: DEFAULT_CYCLE_ID, plexUserId: 'plex-x'}]),
    JSON.stringify([{reservedAt: NOW, cycleId: 'not-a-cycle-id', plexUserId: 'plex-x'}]),
    JSON.stringify([{reservedAt: NOW, cycleId: DEFAULT_CYCLE_ID, plexUserId: ''}])
  ];

  invalidPayloads.forEach(function(raw) {
    resetRuntime();
    runtime.globalStorage.cmaMemberNotificationReservations = raw;
    runtime.globalMutations = [];
    runtime.effects = [];
    const ctx = context(validBody({accountStatus: 'Active', reviewNeeded: false}));
    handler(ctx);
    assert.strictEqual(ctx.response.code, 503, raw);
    assert.match(ctx.response.payload.error, /reservation list/, raw);
    assertNoMutation();
  });
}

function testMalformedOrFutureBudgetFailsClosed() {
  [-1, 1.5, 'not-a-timestamp', NOW + 1].forEach(function(unsafe) {
    resetRuntime();
    seedGlobalBudget(unsafe);
    const ctx = context(validBody({
      accountStatus: 'Active',
      reviewNeeded: false
    }));
    handler(ctx);

    assert.strictEqual(ctx.response.code, 503, String(unsafe));
    assert.match(ctx.response.payload.error, /budget timestamp/, String(unsafe));
    assertNoMutation();
  });

  resetRuntime();
  const unavailable = context(validBody({
    accountStatus: 'Active',
    reviewNeeded: false
  }));
  unavailable.globalStorage = null;
  handler(unavailable);
  assert.strictEqual(unavailable.response.code, 503);
  assert.match(unavailable.response.payload.error, /budget storage/);
  assertNoMutation();

  ['cycle', 'plex'].forEach(function(property) {
    resetRuntime();
    seedGlobalBudget(NOW);
    if (property === 'cycle') {
      runtime.globalStorage.cmaMemberNotificationCycleId = 'invalid';
    } else {
      runtime.globalStorage.cmaMemberNotificationPlexUserId = '';
    }
    runtime.globalMutations = [];
    runtime.effects = [];
    const invalidReservation = context(validBody({
      accountStatus: 'Active',
      reviewNeeded: false
    }));
    handler(invalidReservation);
    assert.strictEqual(invalidReservation.response.code, 503, property);
    assert.match(invalidReservation.response.payload.error, /budget reservation/, property);
    assertNoMutation();
  });
}

function testHealthyReceiptReportsAnExistingServerReservation() {
  resetRuntime();
  seedGlobalBudget(NOW);
  const ctx = context(validBody({
    accountStatus: 'Active',
    reviewNeeded: false,
    notificationMode: 'suppress'
  }));
  handler(ctx);

  assert.strictEqual(ctx.response.payload.result, 'planned');
  assert.strictEqual(ctx.response.payload.action, 'facts-only');
  assert.strictEqual(ctx.response.payload.plannedAction, 'facts-only');
  assertReceipt(ctx.response.payload, {
    mode: 'suppress',
    required: false,
    reserved: false,
    remaining: 14
  });
  assertNoMutation();
}

function testNewMemberOnboardingCreatesOneWelcomeTicketAndRetriesIdempotently() {
  resetRuntime();
  runtime.reporters['member@example.com'] = MEMBER;
  const onboarding = {
    accountStatus: 'Never Used',
    totalPlays: 0,
    watchSeconds: 0,
    watchTime: '0 mins',
    lastStreamedMs: null,
    reviewNeeded: false,
    onboardingRequested: true
  };

  let ctx = context(validBody(Object.assign({
    notificationMode: 'suppress'
  }, onboarding)));
  handler(ctx);
  assert.strictEqual(ctx.response.payload.result, 'deferred');
  assert.strictEqual(ctx.response.payload.plannedAction, 'onboarding-ticket-created');
  assertReceipt(ctx.response.payload, {
    mode: 'suppress',
    required: true,
    reserved: false,
    remaining: 15,
    onboardingRequested: true,
    onboardingCompleted: false
  });
  assertNoMutation();

  ctx = context(validBody(onboarding));
  handler(ctx);
  assert.strictEqual(ctx.response.payload.result, 'created');
  assert.strictEqual(ctx.response.payload.action, 'onboarding-ticket-created');
  assertReceipt(ctx.response.payload, {
    mode: 'permit',
    required: true,
    reserved: true,
    remaining: 14,
    onboardingRequested: true,
    onboardingCompleted: true
  });
  assert.strictEqual(runtime.created.length, 1);
  const welcome = runtime.created[0];
  assert.strictEqual(
    welcome.summary,
    'Welcome to Cameron-Media — Your access is ready'
  );
  assert.ok(welcome.description.startsWith(
    '<!-- CamCore:CMA:onboarding:v1 -->\n\n## Welcome to Cameron-Media\n'
  ));
  assert.match(welcome.description, /https:\/\/app\.plex\.tv\/desktop\//);
  assert.match(welcome.description, /https:\/\/www\.plex\.tv\/apps-devices\//);
  assert.ok(welcome.description.includes('https://camcore.au'));
  assert.ok(welcome.description.includes('https://requests.camcore.au'));
  assert.ok(welcome.description.includes('https://status.camcore.au'));
  assert.ok(welcome.description.includes('provided as part of **CamCore**'));
  assert.ok(welcome.description.includes('**CamCore Operations**'));
  assert.match(welcome.description, /help@camcore\.au/);
  assert.strictEqual(welcome.fields['Review Stage'].name, 'Active');
  assert.strictEqual(welcome.fields.State.name, 'Solved');
  assert.strictEqual(welcome.fields['Account Audit Confirmed At'], runtime.now);

  matchExisting(welcome);
  runtime.created = [];
  runtime.mutations = [];
  runtime.globalMutations = [];
  runtime.effects = [];
  ctx = context(validBody(Object.assign({
    notificationMode: 'suppress',
    cycleId: 'audit-00000000000000000000000000000002'
  }, onboarding)), welcome.project);
  handler(ctx);
  assert.strictEqual(ctx.response.payload.result, 'planned');
  assert.strictEqual(ctx.response.payload.action, 'onboarding-existing-ticket');
  assertReceipt(ctx.response.payload, {
    mode: 'suppress',
    cycleId: 'audit-00000000000000000000000000000002',
    required: false,
    reserved: false,
    remaining: 14,
    onboardingRequested: true,
    onboardingCompleted: true
  });
  assertNoMutation();
}

const originalDateNow = Date.now;
Date.now = function() { return runtime.now; };
try {
  testProjectBoundary();
  testProtocolEndpointIsExactReadOnlyAndCmaScoped();
  testPayloadValidationStopsBeforeSearchOrMutation();
  testFutureTimestampAtSkewBoundaryIsAccepted();
  testHealthyAccountDoesNotCreateOrStampATicket();
  testCanonicalNeverUsedFactsAreAccepted();
  testNewReviewRequiresAReporterBeforeCreation();
  testNewReviewCreationAndFirstNoticeUseSeparatePermits();
  testDuplicateAndCrossIdentifierConflictsDoNotMutate();
  testExistingReporterMustResolveAndMatchBeforeMutation();
  testAuditCallerMustDifferFromReporter();
  testMissingFieldsAndBundleValuesFailBeforeMutation();
  testSuccessfulExistingUpdateChangesFactsAndExactStamp();
  testMutationExceptionEscapesAndCannotStampSuccess();
  testRepeatedDailySyncDoesNotRestartAnOpenReview();
  testActivityAutomaticallyRetainsAnOpenReview();
  testActivityRetainsAStagedTicketBeforeItsFirstNotice();
  testFirstEverStreamByANewMemberDoesNotCloseAReviewThatNeverOpened();
  testRetainedReviewNeedsANewActiveBaselineBeforeRestart();
  testPermitModeNonCandidateIsCompletelyReadOnly();
  testSuppressDefersNewCandidateWithoutAnyMutation();
  testSuppressConservativelyDefersEveryMessageStage();
  testSuppressPlansSafeExistingFactsWithoutMutation();
  testPermitReservesIntoArrayStorageAndTracksMultipleSlots();
  testFifteenConcurrentReservationsFillTheCeilingAndTheSixteenthIsBlocked();
  testEachReservationExpiresIndependentlyOnItsOwnRollingWindow();
  testLegacyReservationMigratesIntoArrayExactlyOnceWithoutLossOrDuplication();
  testMalformedReservationArrayFailsClosed();
  testMalformedOrFutureBudgetFailsClosed();
  testHealthyReceiptReportsAnExistingServerReservation();
  testNewMemberOnboardingCreatesOneWelcomeTicketAndRetriesIdempotently();
} finally {
  Date.now = originalDateNow;
}

console.log('CMA account-sync endpoint tests passed');
