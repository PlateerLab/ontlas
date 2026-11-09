# Changelog

## 0.14.0

- An object, property or relation carries a status: 초안, 사용 중 or 폐기 예정 (`status` in the definition, `STATUSES`). It is set on
  the workspace forms, shown on the cards, the tree and the inspector, and a deprecated element that something still reads says so
  where its uses are listed. A parent is not taken out from under its subtypes: the refusal names them.
- A file in the catalog is read as a person says it is (`POST catalog/use`: data, definition, document, raw, or back to what
  its content says); the row says what it became and that it was set, the draft and the search follow, and a replaced file
  keeps the setting.
- 할 일 says of an action request how much it changes against its automatic-approval limit (변화율 +30% · 자동 승인 한도 10%
  초과), and 팀 전체 is the third tab in a team.
- An answer nothing answers says what the question did name (objects, queries, actions, metrics) and whom to ask: the
  owner of a metric it named. Related definitions include the decision tables behind the rules found and the metrics
  named; a metric leads to 규칙 · 지표 and a decision table to its editor. The home's saved list shows metrics with a 지표 chip.
- A graph perspective is kept by the studio for everyone (`GET graph/views`, `POST graph/view`, `graph/view/forget`), with
  the types shown, each type's colour and the property that names a type's records (`GET records/labels`); in a team it
  survives a restart through the journal. The modelling canvas keeps card positions the same way (`POST workspace/layout`,
  `layout` in `GET manage`), so everyone opening a pipeline sees the same arrangement.
- A record page shows, when a role is picked, only the actions that role may request.
- 과거 판정 다시 계산 on 규칙 decides past cases by the tables as the pending edits leave them (`GET agreement?pending=1`), and
  runs again as a table is edited.
- In a team, applying a reviewed draft (`draft/apply`, `draft/review/apply`, `draft/map/apply`) needs an approver, since it
  replaces the shared space; the page says so and keeps the review. `catalog/move` and `catalog/trash` need an editor.
- The guide (사용 안내) has a section for every screen, including 홈, 할 일, 레코드 탐색, 그래프 탐색, 작업 공간 and 변경 요청, and
  its first steps are the eight steps a person builds an ontology in. The README's how-to follows the same order and its
  screenshots are the current screens.
- Fixed: 객체 제외 on a parent object showed the engine's words; the message is in Korean and names the subtypes.
- The home shows the eight steps an ontology is built in, each with where this space stands on it (`GET build/steps`,
  read from what is here, nothing measured anew), the next step marked, each leading to its screen.
- The ontology cards, the modelling canvas and the record graph zoom with the wheel alone, around the pointer on the
  card canvases; Ctrl is no longer needed. The canvases pan by dragging as before.
- Fixed: opening 모델링 folded the sidebar on its own and unfolded it on leaving, so the menu shrank and grew as a person
  moved between screens. The sidebar stays as the person set it.

- An alert leads to its fix. `GET issues` turns a measurement into what can be acted on: the items behind each failure, the module
  or change that brought them, what reads them and the ways to fix each (here, at once, or at the source with the list to hand
  over). Failures that read a broken column are gathered under it; a failure nothing ties to it stands alone. Which fix is put
  first follows from rules (a close column name to bind to, a module just attached), and without grounds none is. The board's
  alerts, its picture and floors, the home, 할 일, 흐름, DB 대조 and 검증 all open the same panel. A database check finding now
  carries the table, columns and rows it is about (`Finding.data`), and a measurement the queries that disagree and the
  questions a document search missed.
- A link can name what to open on the screen it leads to (`#model?el=property:Sku.expires_on&field=column`), and a screen opens at
  the top instead of where the last one was scrolled to. While a problem is being fixed a bar says which one, what is next and
  where to go back; when the change goes in the board measures again and says whether it is gone. `GET issue/preview` tries taking
  a module off on a copy first. When each issue opened and closed is written to the journal.
- 모델링 작업 공간 is rebuilt around the canvas: the sidebar folds, the panels on either side fold, and the bar along the bottom is gone
  to a toolbar. On the left, objects (found by object, property, relation or column), the source's tables and columns, what is
  wrong and what is pending. On the right, an object and then what is in it, with its properties and relations always in reach,
  each field that cannot be changed saying which module set it, and a data tab with rows and how full each column is
  (`GET object/profile`). On the canvas a relation is drawn from the + on a card to another card, with the join worked out from
  names and how many rows would meet (`GET manage/link/suggest`), a relation line opens when pressed, a column dropped on a card
  becomes a property, cards say what is new, changed or wrong, 연결만 보기 and 문제만 보기 narrow it, and where cards were moved is
  remembered. Any one pending edit can be taken back, later edits kept (`manage/revert`), and one taken back made again
  (`manage/redo`). What blocks a change request is said where it is blocked, and pending edits are checked against the source as
  they are made.
- 객체, 속성 and 관계 are a view of the workspace, three columns side by side: pick an object and the other two follow it, and a row
  opens for editing where it stands. 정의 관리 keeps states and roles and leads to that view; the tables' old addresses open it too.
- 온톨로지 is its own place in the sidebar, under 업무: it is read there and changed under 모델링, which holds 작업 공간 and 정의 관리.
- A question brought by a module can take a new expected answer (`update_question`): a module that removes a question and writes it
  itself keeps its own.

- The page starts from what a person comes to do. The sidebar is three sections, 업무 (home, 할 일, search and questions,
  records, decisions), 구축 (bringing data in, modelling, the library and its changes) and 운영 (the pipeline board, the data
  map, stores and links, checks, the guide), and the first screen is a home instead of the pipeline board.
- 홈: one box to search or ask, what waits on the person, the measured pass conditions in brief, the records they opened last
  and the registered queries. What it leads with follows the role picked on it (운영 담당, 도메인 전문가, 모델러).
- 할 일 (`GET inbox`): action requests waiting for a person, change requests under review, source conflicts to pick and edits
  not filed yet, in one list, each saying who asked and what it would change. An action is approved or rejected from the list.
  On a visitor's own page what they asked for is theirs to settle too; in a team studio it waits for someone else.
- 레코드 (`GET records`, `GET record`): records of a type found by their key or the name they carry, and one record on a page of
  its own: each value with its column or formula, the state it is in and where it can go, the records it links to either way
  round, what each decision says of it now and by which rule, the actions it can take (requested from the page under a role),
  its functions to run, the documents that name it or its type, and its requests, approvals and runs. Opening a page runs no
  function and writes nothing.
- 통합 검색 says what it took the question to be (the record, the decision, the time it counts to) and where the answer came
  from (a decision table or a registered query with no model, a model's wording, or nothing found). What it took can be
  corrected and the same question asked again (`space/ask` with `pick`: another record, another decision of its type or
  none, another time to count days to); the time is the question's only and the studio's clock does not move. A decision's
  answer carries the rule, the clause it cites and the module and version that wrote the rule, and leads to what can be done
  next: the actions the decision gates (their form opens on the record page, ready only when the verdict and the record's
  state allow it), the record itself, and the rules page trying the table on this record. Below it the answer is explained
  three ways: the steps in plain sentences (each value read, where from and along which relations, and why this rule and
  not the others that also held), the values with their records and columns, and the rule's conditions with one SQL query
  that reads the same values from the source. A registered query's answer shows the query it ran, a record its read. Beside
  the answer, a judgement of right or wrong; one judged right is kept as a validation question among the pending edits. A
  question nothing answers is answered that it is not known.
- A decision's result lists the rules that held but the hit policy did not use (`also`), and a decision can be counted to
  another time (`Studio.decide(..., at=)`).
- 변경 요청 (`GET change`, `POST change/mark`, `POST change/comment`): a change request element by element. Each element it
  adds, changes or removes shows field by field what it is now and what it becomes (a rule's condition by its input's name),
  and what in the definition reads it now. The pass conditions show the number the studio meets now beside the number on the
  trial copy, with the validation questions that fail there. A reviewer approves each element or sends it back for a fix, and
  comments stay on the element after the change is decided. A change with an element sent back is not approved. Marks and
  comments go into the journal with the rest of the request. 할 일 opens a change on this screen.
- 규칙 관리 says how a table applies its rules, what the table check finds (overlaps, rules that never apply, inputs no rule
  answers), and tries the table while it is edited (`POST decide/simulate`): a record's values or typed ones, the rule that
  answers, which single change of one input would give another answer, and what the table answers either side of every
  number its rules compare. Past decisions decided again and the validation questions on the table sit beside it. Trying
  writes nothing.
- 초안 생성 scores the draft's tables against every domain standard on its own and shows the match beside each object
  (`결제 · Payment 94%`), with the way to bind the tables to the standard instead of naming new objects.
- 그래프 탐색 (`GET record/links`, `GET record/path`): records as a graph. It starts from one record and grows relation by
  relation, up to 25 records a relation at a time, with the count on each relation before it is opened. Two records are
  joined by the shortest chain of relations that joins them in the data: chains are tried shortest first, up to five hops,
  each as one ontology query, so it runs on the source whatever store that is.
- 모델링 · 작업 공간: the modules and their objects as a tree, the schema graph, and the picked object's form, its lines in
  its module file, and what reads it (`GET element/readers`), side by side. Edits go to the pending changes as on the
  definition screens.
- 초안 생성 is a review of proposals: a stepper that counts what each step still asks a person to settle, each source
  table with the standard object it matches and how well, an English API name from the library's words and the
  glossaries (`주문상태이력` is `OrderStatusHistory`; a name is romanized only when a part of it is no known word), and
  beside the picked table its rows, why its key is a key, the match evidence and the columns to hide
  (`POST draft/table`). Each table is bound to the standard or kept as a new object; the rest are adopted from the
  bar at the foot. The last step shows what applying writes (`POST draft/review/preview`), and applying binds the
  chosen tables to the standard and keeps the others as new objects beside it, joined to the standard's objects where
  the draft found the tables joined (`POST draft/review/apply`). A draft takes object names as an edit (`names`).
- 모델링 · 작업 공간 draws the picked object's module as an entity diagram (keys, computed properties, what other modules
  add, relation names and cardinality, the modules it reaches in their own folding region; cards move by dragging). The
  inspector has the form, the object's YAML as the pending edits leave it, which writes back as the same edits
  (`GET element/yaml`, `POST manage/yaml`), what reads it, and comments kept in the journal (`GET element/comments`,
  `POST element/comment`). A property's form says under the field what the definition check would refuse, with the fix
  as a button. In the toolbar: the pending edits and what they reach, the last one taken back (`POST manage/undo`), a
  trial on a copy of the space (`POST manage/trial`) and the change request.
- 규칙 관리 heads each table with its hit policy (a choice; `update_decision`), its target, its module and the rules
  other modules add; a cell is changed in place; rows move by dragging (`move_rule`). The simulator opens on a record,
  and it, the boundary cases, the validation questions and the table check run on the table as edited.
- 변경 요청 says who reviews and that the author cannot approve, marks each element not yet looked at, lists what the
  change reaches, compares an element field by field or as the module file before and after, and answers a broken
  validation question with a proposal to its author.
- 홈 says when the space was last checked, keeps recent questions, shows which pass conditions a change makes worse and a
  source check that warns as a task, offers records before any was opened, and orders the sidebar for the role.
- 레코드 is read by what it belongs with when it has no name, lists those records a level deeper, has tabs, works out
  read-only functions on opening without logging them, and has the source's own dates in its history.
- 그래프 탐색 starts from a record found by key or name (`GET records/find`), keeps names on nodes and relations, folds a
  relation with many records into one node, saves the shown types as a perspective, lists the steps and copies a link.
- 질의 shows the results first with the code folded below, builds a query without code (an object, a relation, the values,
  conditions) and keeps it as a registered query (`add_query`), and says there is nothing to compare with one store.
- 데이터 카탈로그 says what the files just brought in turned out to be and leads to the next step; the data map's explorer
  is the 자산 탐색기 and an object there leads to its records.
- An edit with an unknown property type or a hit policy the rules cannot take is refused; a rule-level issue no longer
  reads as a decision called "x rule y" when a module is settled.
- The sidebar follows the proposal: 업무 has 객체 탐색 and 그래프 탐색 apart; 구축 has 규칙 · 액션 and 변경 요청 (with the
  number waiting), the library its second tab. A library module shows its change under review and opens in the
  modelling workspace; decided changes are its history.
- 그래프 탐색 draws records as boxes by type with each relation's name, in layers or rings, with the found path in
  orange; relations of the picked record are ticked open and closed; the canvas pans, zooms and fits.
- The modelling diagram follows a pick in the tree, scrolls, pans by dragging the empty canvas, zooms (Ctrl + wheel)
  and fits the width on opening; the modules it reaches stand beside it.
- 초안 생성 opens at its first step, the files and the settings, in the same stepper as the review.
- A record is found as a person would say it (`GET records/find`): a key or part of one in any case, a name, or a
  definition, that is a type's name with words its values hold ("VIP 고객", "취소된 주문": Korean words reach English
  codes through the library's words), a page at a time. On the graph the start and both ends of a path are found as
  they are typed, Enter takes the best match and draws it, a picked box becomes the path's start, a start the graph does
  not hold yet is drawn first, and a window lists many records by type with paging.
- 온톨로지 › 도메인 draws the whole ontology as the workspace's cards, every module a region, beside the picked object's
  definition.
- On 온톨로지 › 도메인 a pressed card gathers what it connects to around it at reading size, in one view: what points at it
  on the left, what it points at on the right, its parent above and its kinds below, on top of the rest of the ontology,
  which stays faint where it was. Another card moves the focus; an empty spot, Esc or 전체 보기 comes back to where the
  person was looking.
- The README's table of screens follows the new sidebar.
- Pending edits hold when they are taken back: a later edit that no longer composes leaves them as they were, one that
  cannot be made again stays to be made, and the last 50 can each be taken back (an older one goes with 모두 취소). A
  source pick is a pending edit like the others, so taking back an earlier edit keeps it. A question that takes a new
  expected answer keeps its params.
- A draft's renamed objects keep their queries' answers and what the review left out, a decision drawn from past
  outcomes on a draft with English names finds its columns, and an English name two tables would share is suggested
  to neither.
- A trial copy reads the same documents, so the document search condition is measured before and after a module is
  taken off or the edits are tried. 할 일 reads the last measurement instead of taking one, a studio from one ontology
  file opens 규칙 · 지표 and the simulator again, and a wrong answer is not put down to a missing column its result names.

## 0.13.0

- A file's embedding is turned on and off on its own, or for a whole folder: its documents leave the vector stores and the search, and
  stay in the draft and in the document ontology. The catalog says per file whether it is embedded, waiting, failed or off, and the
  work record notes each change.
- Every vector carries its file's folder and the model that made it. A model that fails to embed leaves the stores as they were and the
  files it could not embed say so, where it used to stop every search.
- Folders are ranges: a search, a question, the document graph and a relation reading keep to a folder and the folders under it
  (`folder` on `/v1/search`, `/v1/answer` and the MCP tools). A role's `documents` take file paths and patterns such as `정책/*`, and the
  role form offers folders.
- A change of embedding model first lists the documents and passages it embeds again and the time, measured with the new model; the
  stores are refilled only when the change goes ahead. `Space.reembed_plan`, `Space.use_embedder`.
- Relations between a document's concepts are read by a reader port: `basic`, or xgen-ontology-build's relation formation with the new
  `build` extra. Only sentences naming two concepts or more are sent, numbered, so a relation's ends are always concepts its sentence
  names; each relation keeps that sentence. They are rows of the document ontology (`Relation`, `relationsOf`, `relationNames`) and edges
  of its graph, and a named relation replaces the co-mention between the same two concepts. An answer lists the relations its shown
  passages state, and none from a passage the reader may not read.
- A word that is only an ending (하는, 되는) is no longer taken for a document's keyword.
- A reading runs on the server with its progress, stops and resumes, covers a folder or everything, and is kept with the repositories.
  A passage that changes is read again. It replaces reading one section per request, which kept nothing across restarts and stayed
  out of search.

## 0.12.0

- An interface is queried like a parent type: `{match: {x: Named}}` reads every type that implements it, on every store. A role reads
  through it only if it reads each of those types without a row limit, and it sees the strictest mask among them.
- Functions are a section of the ontology: inputs, outputs, version, owner and status under one contract, carried out as an expression,
  a decision, a query, a callable the deployment registered or a service on an allowed host. A role is given one by name. `/v1/functions`,
  `/v1/function`, MCP `list_functions` and `run_function`, `xspace functions` and a tab under definitions. An action can take one as a condition.
- `approval: {auto_within: [...], agents: false}`: inside its limits an action runs at once, past them a person approves. A limit reads a
  change (`delta`, `percent`) or a value (`max`, `min`), by number or named value. The request records how it stood.
- `transform` and `source_type` on a property: how a column becomes its value, compiled into every language.
- `flow.values` and `max_value_errors`: what the ontology answers held case by case against what the transaction system recorded or answers
  now. `xspace values` and a card on the check screen.
- OpenAPI 3 and Swagger 2, in JSON or YAML, read as tables, references and code groups, and each writing operation as a drafted action.
- Forms for what was module text only: adding a named value, metrics, identities, an action's limits, values it sets and outside calls, a
  role's rows and organisation scope, a property's transform. A row rule the form cannot say is kept as it is.
- `/v1/context` and MCP `agent_context` give what a question is about as text for a prompt. `/v1/openapi.json` carries the address it was
  reached at, and `query` is declared a string, which a parser that wants a type can read.
- Fixed: `/v1/actions` dropped the connection when a row held a decimal. An action that only calls out wrote an empty update. A crosswalk not
  written yet no longer fails the database check or the graph load of a copy.
- A README section on prior art.
- `--journal FILE` keeps requests, approvals, change requests and the audit trail of a team studio across restarts; `xspace mcp --journal`
  does the same for an agent's process. Before, a restart forgot who asked, who approved and what a change replaced.
- A request is settled by a person other than the one who asked, with the right to execute it on that row. A request that ran can no
  longer be rejected, which left the record saying rejected while the source kept the change; it is rolled back instead.
- `--api-agents FILE`: one token per agent, each with its own name, role and rows. `/v1/proposals` gives a token its own requests,
  `/v1/record` one object by key; MCP gains `get_record`, and `list_proposals` gives an agent with a role only its own requests.
- A role can list the documents it reads (`documents:`); search, answers and the document list keep to them. The role form has them.
- The audit trail names the module versions and the matched rules, and an agent's decisions, answers and functions go into it.
- The adapters screen shows what was measured, not what is known: every registered query compiled for each language (with the reason
  for any that cannot be), the stores' agreement, each reasoner's run, and the modules the current pipeline is built from instead of
  the example library's names. The tests run once when the screen opens; the configuration notes moved to help.
- A data explorer opens the data map: everything the space holds as folders, from repository files to tables and columns,
  documents, objects and properties, stores, queries and decisions, each row with what it went through (indexed as a
  document, in the draft, mapped to an object). One search covers names and paths, definitions and document text by words and
  by meaning, and says which of them found each hit; when only the meaning search answers, it says these are the nearest
  documents. Files and folders can be moved and renamed there.
- Deleting a file or a folder puts it in the repository's trash, from which it is restored where it was or deleted for good;
  its bytes stay, and count against the limits, until then. Items restored together come back all or none when a name is
  taken. A repository keeps a work record of uploads, moves, renames, deletions, restores and what goes into a draft.
  `catalog/move`, `catalog/trash`, `catalog/history`.
- `{@name}` inside a rule's output text puts the named value in force there.
- Fixed: a decision table read a database amount as a Decimal, which the ZEN engine refused, so the page always said ZEN failed for it.
- The page: requests that ran stay listed with their rollback after the page is left; a request names who made it, a person or an
  agent, and says why one inside its limits still waits; a refused approval says why in words; a change that fails its review lists the
  questions and values that differ; a named value lists what reads it; a fixed row rule offers the allowed values; database errors and
  findings say what to do; each screen's help says why it works as it does. An example's own names left the manual.
- The foot of the sidebar shows what the space is connected to, tried when the page opens and every 30 seconds, under stores,
  languages and links: each store answers a one-row query (its kind and response time, or why it did not), the vector stores, the
  embedding model, the language model by how its last call went, and the REST API. It replaces a card that named the domain
  modules and listed the stores by their configuration keys with a dot that was never measured. `GET connections`; a store class
  says its `kind`.

## 0.11.0

- XGEN Space is open source now, under the Apache License 2.0. Versions before this one stay under the terms they shipped with.
- A space holds documents and vectors now, not only an ontology. Vector stores (memory, Qdrant over REST, pgvector) and
  embedders (hash, any OpenAI-shaped service, a local multilingual model through fastembed) are ports with a registry;
  `xspace vectors` holds every store to exact search, and a tie at the cut is not counted as a difference.
- A document goes two ways: cut, embedded and written to every store, and turned into a document ontology of documents,
  sections and concepts that runs on the same compilers. Concepts tie it to the domain ontology: a search names the
  definitions a question speaks of, and an object shows the sections that mention it. A language model can read relations
  from a section; one is kept only if both ends are words of that text.
- Reasoners are a port too (rules, owlrl, shacl, reasonable, any HTTP service). `xspace reasoners` compares engines of one
  logic, which found that reasonable 0.4.4 joins every subject of an inverse functional property with sameAs, so it stays
  off the default list.
- Other platforms come in through `/v1`: a token, a role, OpenAPI at `/v1/openapi.json` and function definitions at
  `/v1/tools`, off unless `--api-token-env` is given. MCP gains `search_documents`, `list_documents` and `describe_space`.
- `kind: gateway` reads through a platform's query service, so a space can use a connection the platform manages without
  ever holding its password, and never writes. An answer that comes back full is marked as possibly cut. Also on the page.
- `.doc`, `.ppt` and `.xls` (Office 97 to 2003) are read with the standard library: a data sheet in `.xls` comes in as rows
  and a definition sheet as definitions, as `.xlsx` does. A file with a password, or from before 97, is refused with what to
  do. Tables of one name in two schemas are both kept, as `schema.table`.
- SQL Server joins: `kind: mssql`, `mssql://` and `sqlserver://` in `xspace draft --dsn` and on the page, drafted from its
  catalog with composite keys. Oracle now runs on a real server: identifiers follow the catalog's case, dates are ISO in the
  session, an empty text literal asks for null. Both pass conformance on live servers (Oracle Free 23, SQL Server 2022); the
  `[oracle]` and `[mssql]` extras need sqlglot 29. `fetch` works on an integer key.
- Conditional aggregates: `sum(link.prop where cond)` in computed properties and `{"sum": ..., "where": ...}` in query columns,
  on every language. Gremlin compiles optional links and computed properties. GQL and SQL/PGQ compile link aggregates and date
  functions; SQL/PGQ is verified on Oracle 23, GQL is checked as text only. A column named like its alias is valid SPARQL now.
- The sidebar is the board, the map and the six stages in order; a stage's screens are tabs on its page, and a stage opens on the
  tab left last. The sidebar folds to a rail with a handle on its edge, with names on hover, and stays folded on the next visit.
- A tab does not repeat its stage's word, and screens of one thing are one tab with a switch: ontology (domain, documents),
  definitions (objects, properties, relations), decisions and rules. The board keeps to the window's height whatever its floors.
- The data map's panel says what a node is, opens its screen, and groups what it reaches by kind. The rules screen leads with a
  summary per decision table, details on request. Labels and help on the newest screens read in the product's terms.
- Search orders what the store found by the model's score and the question's own words. Stores are still compared on the model alone.
- Decisions: hit policy `priority` shows what it overrode, and `findings` report overlaps, unreachable rules and input gaps.
  `parameters` are one named value read as `@name` by rules and expressions, changed alone by a customer module. Dates kept as
  text read as dates with `format: YYYYMMDD`, and `period` with `current(link.prop)` gives the row valid now. Scoped roles limit
  reads and writes to the signed-in organisation and fail closed. `metrics` return a number with its formula, denominator, time
  basis and owner. `conflicts` hold rules of two sources that disagree until a person picks. Transitions take a guard, side
  effects and `after`, and an action is asked again right before it runs. `view` defines an object by a query, in the source or
  carried along with `inline: true` where the source cannot be written. A rules screen shows all of it.
- The asset ontology is drawn as a map of files, tables, documents, stores, objects and queries, with what a change reaches.
- Pipelines outlive a restart where repositories do. A connected database keeps its modules and asks to be connected again:
  no address or token is written.
- The board has a storage floor and the flow an index stage with a pass condition on document search. Six new screens
  (data map, document ontology, vectors, adapters, document search, integrations), a guide rewritten around them, help for
  the screen in hand, and first steps for a new visitor.

- What a person approves reaches every way in. With `--users`, `/v1` answers from the studio the team shares, a running
  `xspace mcp` reads the library again once a change is saved there, and the `workspace` module comes back at the next start.
- The decision page lists every request waiting for a person, whoever filed it: another person, a platform or an agent.
- A matched rule in a decision table stays a table row; the style of a search result had turned it into a column.
- Words on the page and in the reasons the server writes are the product's own.

- One question over everything. Definitions, rules and passages sit in one index behind a retriever port (`words`, or `omnifuse` for
  fusion with the graph between them), and a question goes to the decision table, the record, a registered query or the passages. A
  decision needs no model. The page's 통합 검색, `/v1/answer` and the MCP tool `answer_question` are the same code.
- An agent reads less: `find_definitions` and `describe_object` give what a question is about instead of the whole ontology.
- Rules, named values, states, actions and roles are edited on forms, the same way as objects: an edit, a trial on a copy, an approval.
  A decision can replace or remove a rule of a standard over it (`rules_replace`, `rules_remove`) and an action can be extended.
- A decision table reads in people's words: labels for inputs, `14일 이하` for `<= 14`, and an amount is no longer shown as a refusal.
- The rows under an object can be read from its screen, and an earlier version of a module can be filed again.
- With `--library-write`, what is switched on stays on across a restart, and a kept module that stopped fitting cannot keep a studio down.
- `xspace compare` puts one question file to one model three ways: with nothing, with the documents alone and through the space.

- A graph stays readable at a customer's size: past 120 nodes it opens folded into its communities, a node shows its first or second neighbours, and two nodes show the path between them. Labels keep clear of nodes.
- The wrong answers on the check screen are grouped by cause, and a question a model is working on no longer holds up the rest of the page.

## 0.10.0

- The example library is e-commerce alone. `commerce-operations` adds sellers, payments, refunds, carriers, shipments,
  coupons, reviews and a shipping fee decision, and the shop grows to 27 customers and 70 orders
  (`tools/make_commerce_seed.py`, a fixed seed, all invented). The sample files are the shop's raw CSV files.
  The finance package and the book lending files moved to `tests/fixtures`, so what two domains show stays tested.
- The graph is drawn with sigma.js on WebGL: colour by module, or by detected community when one module holds all, size
  by connections, curved edges with arrows, a selected type lighting only its neighbours, search, six layouts, rotation,
  full screen. Layouts run once and stop. The engine is a separate file, loaded the first time a graph opens.
- The in-memory graph answers a long path. rdflib ran every `?x a :Type` first, so a query over five hops became the
  product of five classes and a measurement of the pipeline never ended on real row counts. A basic graph pattern now
  walks along what it has bound: 70 orders across five hops went from minutes to 0.1 seconds.

## 0.9.0

- `.hwp` (Hancom 5.x) is read with the standard library: text by section, tables' cells included. A file with a password
  or a viewing-only copy is refused with what to export it to.
- Images, video and archives in the catalog are kept as raw files instead of showing as failed reads.
- Terms of art are written in English on the page: Domain Adapter, Binding, Cardinality, Backend, Interface, Action,
  Parameter, Node, Edge, Mapping, Agent, Schema.
- The draft screen no longer breaks after a file is left out of it, and a switch of pipeline clears the policy, mapping
  and decision forms it left behind.
- A decision table is no longer offered date columns as inputs, which it cannot use. A module with a field missing, a
  wrong type or an unknown target, a typed query and a table drawn from past cases now answer in the product's words.
- A database that does not answer gives up after 10 seconds and says so, without repeating the address's password.
- 경로 입력 with nothing typed is refused; it used to bring in the folder the server runs in.
- A question's expected answer is checked before it is saved. A heading with no text is not offered as a policy section.

## 0.8.0

- Pipelines to choose from: each applied draft is kept beside the ones before it, and the list at the top of the page
  switches between them with their modules, data, changes and history. Up to five, and they end with the visitor.
- Product wording across the page: 레포지토리, 드래그, 규모, 통합 JSON, 메뉴 검색, 알람, 장애, 연쇄 장애, 장애 테스트, 점검.
  The board drops its English captions and slogans, and the demo's captions follow.

## 0.7.0

- 파이프라인 관제, the page's new first screen: the pipeline as a building of five floors (원천 데이터, 변환, 온톨로지 구축,
  활용, 검증), drawn from what the space holds now. Numbers refresh every 2 seconds; the flow is measured again at once
  when the definition or the files change and otherwise every 20 seconds, only while the board is open.
- A stage that misses its pass conditions stops the data at its floor, and a failure that crosses floors is told as a
  chain down to the module that brought it (`web/monitor.py`). Files that could not be read and changes or actions
  waiting on a person show as warnings.
- `monitor: {faults: [{label, attach}]}` in a studio file lists modules the board can apply to show a real failure, and
  take off again.

## 0.6.0

- The product is XGEN Space now: repository `xgen-space`, package `xgen_space`, command `xspace` (it was
  `xgen-data-studio`, `xgen_data_studio` and `xds`), environment variables `XSPACE_*`, request header
  `X-XSPACE-Request`. Earlier entries below keep the old names.
- 데이터 카탈로그: repositories of raw files, by folder (`repository.py`). Files and whole folders are uploaded by drag
  and drop or a picker with their structure kept; each row says the file's kind, format, size, rows or sections, upload
  date and where it goes. A file that cannot be read is kept with the reason. Rename, delete, download, sort, filter by
  extension, select several. A path is a name in an index and the bytes are stored by hash, so nothing a visitor types
  reaches the file system.
- `xspace serve --repositories DIR` keeps repositories across restarts for all visitors; without it they end with the
  visitor. `--max-files` and `--total-mb` set the limits (30 files by default, up from 8). `--allow-connect` also brings
  in a file or folder from the server's disk.
- What goes into a draft follows the catalog: a file or folder left out stays in the repository, and switching
  repository switches what the draft reads. `/api/upload` takes `path` instead of `name` and keeps an unreadable file
  instead of refusing it.
- 변환 결과: what each file came to and the one JSON they roll up into, with a download. A data file brings its columns
  and types, not its rows.
- The page: stages in a side menu that folds (① 원천 데이터, ② 변환, ③ 온톨로지 구축, ④ 활용, ⑤ 검증), a breadcrumb bar,
  a repository picker, `Ctrl K` to any screen. DB 연결 is a screen of its own; 데이터 연결 became 초안 생성. A neutral
  palette in the page and the static preview.
- A download's file name is sent as `filename*`, so a Korean name no longer breaks the header.

## 0.5.0

- Computed properties (`expr`): arithmetic, comparisons, `coalesce if abs round floor ceil lower upper length concat
  year month day days_between`, aggregates along link paths (`sum avg min max count`) and `latest` / `earliest` on a
  series (`series: {time, of}`), typed and checked for loops, compiled into SQL (scalar subqueries), SPARQL (`BIND`,
  grouped subqueries, day numbers from the date's digits) and Cypher (pattern comprehensions folded once with
  `head([l IN [list] | ...])`); GQL and SQL/PGQ take the ones without links and dates and refuse the rest. Never
  projected into a graph, so conformance compares the expression across backends. Nulls: division by zero and an
  `if` on a null condition give null. The SPARQL reader reads a computed property's `BIND` back by name; the page's
  editable SPARQL and Cypher write computed properties by name.
- The IR orders by `alias.property` as well as by a returned column, and by a property it does not return (a hidden
  column the studio drops), for queries without aggregates.
- Masks: `mask: partial | full` on a property, `mask` and `unmask` on a role; a computed property built from a masked
  one is masked; filtering or ordering on a masked property is refused; decision evidence follows the role's masks.
- Actions: parameter specs `{type, required, min, max, values, pattern, max_length}`; `call` sends an external request
  after the change is written, only to `actions.call_hosts`, with `${ENV}` filled into headers only, and a failed
  request puts the row back (`failed`); `ActionService.rollback()` restores the values an executed action replaced
  when nothing has changed them since, and sends `undo` for an action that called out.
- Identities: `identities:` with members, match fields and rules (normalize `lower digits trim alnum`) become an object
  and one link per member over a crosswalk; `Studio.resolve_identity()` joins the records (union of rule matches, with
  evidence and the same-system duplicates it finds) and writes the crosswalk in one transaction (`run_many`).
- `review`: the flow's stages and pass conditions (`flow: {off, gates, agreement}`: database errors and warnings,
  backend agreement, agreement with past decisions, question accuracy), `Studio.gates()`, `Studio.agreement()`
  (past cases decided again with the values they had then, the cases that differ with the rule that fired, a
  confusion table), and `ChangeService`: a module version proposed, tried on a copy of the studio, reviewed (added,
  removed and changed elements, the measures, the gates), approved by someone other than its author when it passes,
  saved to the library and swapped in.
- Drafts gain state machines (a status column; transitions and the first state read from a table of past states,
  which becomes a series), one action per state things move into, roles (viewer, operator, a person's own rows),
  questions (each generated query with the rows it gives now) and decision tables drawn from past outcomes
  (`induce`: a shallow decision tree, each rule with the cases it covers and gets right, five-fold cross-validation).
- `mapping`: tables and columns matched onto a standard module (names, labels, aligned vocabulary, romanized Korean,
  types, allowed values, keys; relations from the draft's), and a binding module from the confirmed matches that
  leaves out what the tables do not carry, and the computed properties, queries and questions that need it.
- Gremlin: `compile/gremlin.py` (TinkerPop 3.8 scripts with every value a binding; `repeat().emit()` for hops,
  `where()` filters, grouping from per-row maps) and `GremlinBackend` (Gremlin Server; a projection loaded with one
  list binding per script, within the server's binding limit). Backends declare which computed properties they take.
- `DbApiBackend` closes the transaction a read opens (no idle-in-transaction locks) and rolls back after a failed
  statement; `run_many()` runs writes as one transaction on SQLite and DB-API.
- The page: flow pass conditions and settings (stages, conditions, the agreement mapping), reading the source again,
  change requests with their review and approval, agreement and rollback on the decision screen, computed properties,
  masks, series and identities on the ontology screen, masked columns in results, the draft's rules step with a
  decision drawn from outcomes, and binding uploaded files onto a standard. `xds serve --users users.yaml`: a team
  signs in (PBKDF2, HttpOnly SameSite=Strict cookie, writes only with the page's header and origin, sign-in attempts
  limited) and shares one studio; viewer, editor, approver, admin. `--library-write` saves approved versions to the
  library folder; `--sync N` reads the source again every N seconds.
- `nl`: the schema card shows computed properties with their expressions and descriptions, link cardinalities and
  the property each registered query's parameter is compared with; an answer that finds no rows goes back once with
  sample values of the properties it compared; a model that does not answer in time is a failed attempt.
  `nl.evaluate()` and `xds nl-eval` score a model by execution against gold queries.
- Commands: `xds gates`, `agreement`, `identity`, `review`, `sync`, `nl-eval`, `users add | list`; `serve --users
  --library-write --sync`. Extras `[gremlin]` and `[live]`; `tests/test_live.py` runs on PostgreSQL, Fuseki, Neo4j and
  Gremlin Server when their addresses are set, and a CI job runs it against service containers.
- Examples: a price history, computed totals and the purchase amount without cancelled orders, a masked phone number
  and a support role, a customer who is also a borrower (`party-identity`), past return cases and the flow's pass
  conditions, a loan status history among the sample files, sixteen plain-language questions with gold queries.
  Revenue by category sums line totals (it summed unit prices).
- Two more module kinds, so the way a definition is checked and the way a draft is built plug in and out like the
  definition itself: `quality` carries questions and `flow: {gates}` (an attached module holds the studio's pass
  conditions to its own where they ask more, and detaching it lowers them again; the page shows which module set a
  condition) and `method` carries `draft_rules` (the defaults the data tab drafts with). Examples `return-quality` and
  `build-rules`. A change to a quality module is reviewed against the bar it sets.
- Grounded answers: each question reports whether its answer carries its condition (the rule that matched, or the
  query), its source (the rule's cite or its table's, the source column of each value) and the version it was
  answered by, and what it lacks; `QuestionReport.grounded` and the pass condition `check.min_grounded`. The return
  decision of the single-file commerce example cites its policy clauses.
- `mapping`: a column only one type has goes to an inherited property only (an order's agreement date), never to a
  type's own property or an ancestor's key (a SKU number took the order number); a relation joins on the first
  property matched to a column. A binding over tables without the columns a state machine, a decision or an action
  needs takes those out (`remove: {states: [...]}`; removing an action takes it out of the roles that held it), and
  the standard's questions answered on its example data are asked again with the answers the tables give, or left
  out when they cannot be answered; each kept query without parameters is asked its row count.
- `policy`: a decision table drafted from policy text by a language model and checked by the engine (inputs on the
  target or along a path, evaluable tests, known outputs, and a cite for every rule that the text numbers), sent back
  with what is wrong, and written as a module a person files as a change request. On the page with `--llm-url`:
  "정책서로 규칙 초안" in the library (`--policies DIR` for example texts); `xds policy-draft`. Example
  `examples/policies/교환정책서.md`.
- `nl`: a returned column named after another property of its object (`c.customer_id` as `name`) goes back to the
  model; on the page a question tries again only within 45 seconds of starting, so it ends before a proxy in front
  (Cloudflare, 100 s) gives up, and an answer that fails says what the model last got wrong.
- `manage`: the page's data management screens, before the library: 데이터 소스 (the source's tables with rows,
  columns, keys and references, and the objects and relations that read each; a relation's junction table counts as
  read), 객체 관리, 속성 관리, 관계 관리 (with the relations the source's foreign keys suggest) and 검증 질문 관리 on the
  checks screen (add, remove, import a YAML or JSON list). Every edit goes into one overlay module, `workspace` (kind
  `customer`, "관리 변경"): what it defines it changes directly; a standard's elements it extends or removes, and a
  standard's type and key and an inherited property are refused there. An edit that leaves the module's own element
  broken is refused. The edits are filed as one change request and tried on a copy; one the trial stops is sent back
  with its review and the edits stay. Routes `manage`, `manage/edit`, `manage/questions`, `manage/discard`,
  `manage/propose` (editor).
- `modules.settle()`: takes out of a module's reach what its removals leave broken in the modules under it (queries,
  decisions, actions, questions, links, identities, state machines, properties), skipping what the module defines;
  `mapping.binding()` uses it. Removing a property or an object also takes it out of the roles that read, filter or
  mask it.
- The page's menu is grouped (시작, 데이터 관리, 온톨로지, 활용 · 검증), and a change review lists what the database check
  found.
- Value names: a property's allowed values carry their names (`labels: {value: name}`, or `values: {value: name}`
  at once); an extension adds names to the ones given; a name for a value the property does not allow is reported.
  The page shows them with the values and edits them as `value=name`.
- `definitions`: table and code definitions read from CSV or Excel sheets (Korean and English header names; a nullable
  flag or a required one; a type with its length; a code group named in a column's name) or JSON. `draft(...,
  definitions=)` names objects and properties from them and gives coded columns their values with their names;
  `schema_backend()` builds an empty database with the declared keys and single-column references, so a studio is
  drafted from the schema alone. A table keyed by several columns is skipped as `composite_key`. `xds draft
  --definitions FILE [--tables PATTERNS]`; the data tab takes definition files beside data files (or alone).
  `DraftRules.table_prefixes` (default `tb_`, `tbl_`) are left out of object names. Example
  `examples/definitions`.
- `ingest`: anything rolls up into one JSON (`xds ingest`, the data tab). SQL scripts in five dialects, `.dbml`, `.pdm`,
  `.mwb`, SQLite files; table, index, code, glossary and message sheets behind a cover sheet and under a title, with
  a code definition's group rows and reference columns; Word, PowerPoint, Hangul, PDF, HTML, Markdown and text documents by
  section. Zip formats are capped when unpacked and XML entities are refused. Other formats plug in with
  `ingest.register` (`--adapter`, `XDS_ADAPTERS`).
- Composite keys: a property reads several columns (`columns: [a, b]`). A key stays one property above the columns;
  SQL joins column by column, writes and the database check read each one, SQL/PGQ and R2RML name them all. Drafts keep
  composite primary keys and references, and a binding can read a standard's key from several columns.
- MySQL and Oracle: drafted from their catalogs (`[mysql]`, `[oracle]`) and checked on live servers. Profiling casts
  through each dialect, so json and CLOB columns no longer stop a draft.
- `codetables`: a code group whose references name other code groups becomes a decision table: a stored code decides
  what it implies, and otherwise each state collects the codes it allows.
- `dictionary` modules hold a system's terms and messages. A glossary finds the standard's names in `mapping.suggest`
  and reaches the schema card; a decision answering with a message code shows the message.
- `mapping`: a name inside a longer one counts as near, a table named as the thing itself goes ahead of its detail
  tables, a standard's key takes all the columns of a composite key, and a table chosen by hand is matched again
  (`retarget`). `settle()` also clears a title, an interface or a series the tables cannot fill.
- Policy drafting reads any document: `xds policy-draft` takes the file, and the page offers uploaded documents by section.
- A policy draft runs apart from the page request (`policy/draft` starts it, `policy/draft/result` collects it) with
  a budget of its own, 12,000 tokens and 200 seconds a call: a model that reasons first used over 4,000 tokens on a
  six-line policy and left the answer empty. The visitor's other requests no longer wait behind it, an answer cut off
  by the token budget is told apart (`AnswerCutOff`) and the page says so in plain words. Rules may cite headings
  numbered `2. 반품 제한`; a bare number cites a heading, not a digit somewhere in the text.
- The README says what the studio is for and how a domain is adapted; the page's guide opens with the same. The
  overlay module is labelled "관리 변경", and a draft's default names are no longer possessive.
- The README says what sets the studio apart and how to use it, step by step and screen by screen, and installs from
  a checkout (the package is not on PyPI). `xds draft` expands its own wildcards, for shells that leave them as they
  are (PowerShell).

## 0.4.0

- `draft`: a definition and its bindings drafted from files or a database, every choice kept with its reason.
  Tables become objects (the W3C Direct Mapping), a table of two relation columns a many-to-many link; keys are
  the declared primary key or a column of present, distinct values (a row number for files that have none);
  types are declared, or read from the values for files (thousands separators, dates in several spellings, codes
  with leading zeros kept as text); repeating text values become allowed values; relations are declared foreign
  keys, or a column named after another table's key whose values all appear in it. A list, a count per relation
  and a count per allowed value are generated as queries. CSV (UTF-8 or CP949, any common delimiter) and Excel
  (`[xlsx]` extra); the SQLite catalog and the PostgreSQL information schema.
- `xds draft FILES | --sqlite PATH | --dsn DSN`: prints the two modules, or with `-o` writes a library, the loaded
  data and a studio file that `xds serve` and `xds conformance` take as they are.
- `DraftRules`: every rule the draft decides by (allowed-value limits, relation inference, link tables, row keys,
  the title, parent, key-suffix and generic-key name hints, the kinds of generated query), with the defaults above;
  `xds draft --rules`. `Draft.revise()` takes keys, types, allowed values, labels, left-out objects, properties and
  queries, cardinalities and relations added by hand. `load_sqlite(types=...)` loads a column as the type a person
  chose; a value that does not fit raises `ReadError(reason="convert")` with its table, column and value.
  `ReadError.reason` names why a file could not be read.
- `OverlayLibrary`: modules held in memory over a library folder, so a draft plugs in next to the saved packages.
- `Studio.replace(module)`: swap a plugged-in module for an edited version, refused if the result does not hold.
- The page: a flow tab with every stage of the studio and what it holds now; a data tab that takes uploaded files
  (within size and row limits, `--file-kb` and `--rows`, kept in memory for the visit), builds the draft step by step on the schema graph,
  shows the reason for each object, key, type and relation and the module files, lets a person leave out and
  rename, and plugs the result into that visitor's studio. `--samples` offers example files; `--allow-connect`
  lets a studio inside your own network take a database address.
- The page lets a person adapt every layer: the draft rules and the tables to draft from; on each step the key, a
  property's type, allowed values and label, a relation's cardinality and label, relations added by hand and the
  generated queries, with the definition checked after each change and the errors shown before it can be plugged
  in; and on the library tab any module as its file, checked, saved into that visitor's library, swapped in when
  plugged in, or downloaded. New modules start from a template.
- A guide tab: what each screen is for and what to try on it. With `xds serve --video demo.mp4` the demo plays
  beside it (served in byte ranges so it can seek), its chapters (`demo.chapters.json`) list next to the player,
  and the chapter playing lights up its section; each section starts the video at its own chapter.
- SPARQL: an aggregated query is ordered by its selected names; rdflib dropped the grouped variable and returned
  the groups unordered.

## 0.3.0

- `xds serve`: the studio page as a working application on the standard library's HTTP server. Library tab with
  switches that plug modules in and out (the impact first, dependents offered together), the schema graph
  (laid out once and still, modules as dashed groups, concepts as rings), one query in seven languages with the
  rows from every backend, SPARQL, Cypher or IR written by hand and run everywhere, queries under a role's row
  filters, decisions with the rule, its citation, the evidence path and the same verdict on ZEN, an agent's
  request checked and approved by a person with the change written back and projected, the validation questions
  and conformance, the database check, OWL and JDM downloads.
- Every visitor gets a studio of their own from the same studio file (one kept ready ahead), dropped after an
  idle hour; the page is one HTML response with its style and script inlined, so a cache in front never mixes
  versions.
- `nl.openai_chat(url, model)`: an `llm` callable for any OpenAI-compatible endpoint; `xds serve --llm-url`
  adds a question box.

## 0.2.0

- Modules: domain knowledge packaged as common concepts, domains, industry extensions, a customer's
  differences and database bindings; composed in requirement order with the origin of every element,
  extended (properties, enum values, columns, decision rules ahead of or after the standard ones, role scope)
  and trimmed (`remove`); attach and detach at run time, with the impact of a detach shown first.
- Library: versioned packages kept apart on disk; list, create, save a version, diff, delete (refused while
  another package requires it), resolve requirements, import an OWL standard as a package.
- Concepts: a type without a table is queried through its bound subtypes (SQL `UNION ALL`; SPARQL and Cypher by
  the concept's type), so one question reaches every domain that specialises the concept.
- Provenance: `cite` on types, properties, links, decisions, rules and actions; `aligned` IRIs to public
  vocabularies; OWL export with `skos:exactMatch`, `dcterms:source` and `rdfs:isDefinedBy`; import keeps the source IRIs.
- Database check: tables, columns and types against the definition, duplicate keys, missing required values,
  enum values the definition does not know, links that point at nothing (`xds bindings`).
- The studio page gains the ontology library tab; the schema graph shows each type's module and its concepts.
- Example library: common concepts, commerce, commerce bindings, fashion, food, a customer overlay, finance
  aligned to FIBO, finance bindings.

## 0.1.0

- Metamodel: object types, properties, links (on / via), interfaces, state machines, decision tables, actions,
  roles with row filters, registered queries, validation questions; JSON and YAML, with consistency checks.
- Ontology query IR with checking (link direction, inverse names, types, parameters, connectivity).
- Compilers: SQL (PostgreSQL, SQLite; other dialects through sqlglot), Cypher 25, ISO GQL, SPARQL 1.1, SQL/PGQ,
  and CREATE PROPERTY GRAPH for the bound tables.
- Backends: SQLite, any DB-API connection, rdflib, SPARQL 1.1 endpoints, Neo4j, a callable adapter; capabilities.
- Projection of source rows to RDF and property graphs, with change sets for incremental loads.
- Readers for SPARQL and Cypher into the IR, so a query in either runs on any backend.
- Decision tables (first / collect / unique) with evidence, GoRules JDM export and ZEN evaluation.
- Actions with checks, human approval, SQL write-back and an audit trail; role scoping for queries and tools.
- Rules (inverse, symmetric, transitive, shape checks), SHACL generation and validation, OWL RL materialization.
- OWL and R2RML export with an exchange report; OWL/RDFS import.
- Asset catalog: what an agent sees, what a change touches, what nobody uses.
- LLM assist: schema card, IR generation with check-and-repair.
- Conformance runs across backends, `xds` CLI and an MCP server.
- `xds preview`: a studio page (ontology, one query on every backend, a decision, the data map) built from
  live results; `tools/render_screens.py` captures it for the README.
