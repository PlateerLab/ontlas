# Changelog

## 0.11.0

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
- The asset ontology is drawn as a map of files, tables, documents, stores, objects and queries, with what a change reaches.
- Pipelines outlive a restart where repositories do. A connected database keeps its modules and asks to be connected again:
  no address or token is written.
- The board has a storage floor and the flow an index stage with a pass condition on document search. Six new screens
  (data map, document ontology, vectors, adapters, document search, integrations), a guide rewritten around them, help for
  the screen in hand, and first steps for a new visitor.

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
