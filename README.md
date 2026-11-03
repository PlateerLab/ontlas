# xgen-data-studio

**One domain ontology, executed wherever the data already lives.** Describe the business once (object
types, properties, links, states, decisions, actions, roles) and bind it to the source tables, or draft both from
the tables and files you already have. A question
then becomes *one* ontology query, and the studio compiles it for the store a deployment actually has:
SQL in any dialect, Cypher, ISO GQL, SPARQL, SQL/PGQ or Gremlin. Computed properties (a line total, an order total
over its items, the latest price of a series) are part of the definition and compile into each of those languages.
SPARQL and Cypher written by people or agents are read back into the same query, so they run on any of those stores
too. **Zero hard dependencies, zero infra to try it.**

```python
from xgen_data_studio import Ontology
from xgen_data_studio.studio import Studio
from xgen_data_studio.backends.sql import SqliteBackend
from xgen_data_studio.backends.rdf import RdflibBackend

studio = Studio(Ontology.load("examples/commerce/ontology.yaml").check())
studio.add_backend("source", SqliteBackend()).script(open("examples/commerce/seed.sql", encoding="utf-8").read())
studio.add_backend("graph", RdflibBackend())        # a graph only when you want one
studio.project()                                   # source rows -> RDF; later calls send only what changed

studio.run("revenueByCategory")                    # compiled to SQL, run on the source
studio.run("revenueByCategory", backend="graph")   # the same query as SPARQL, the same rows
studio.translate("revenueByCategory", "sql:oracle").text      # or cypher, gql, sparql, sqlpgq, sql:mysql, ...
studio.run_cypher("MATCH (o:Order)-[:hasItem]->(i:OrderItem) RETURN o.order_id, count(i) AS n")  # on SQL
studio.decide("returnEligibility", "I1001")        # outputs, the rule that fired, the columns it read
```

<p align="center">
  <img src="assets/architecture.png" alt="One ontology definition feeding execution adapters that compile one query IR to SQL, Cypher, GQL, SPARQL, SQL/PGQ and Gremlin for the backends a deployment has" width="920">
</p>

## What it looks like

The screens below are the studio page that `xds preview` writes for the example library in `examples/library`
(common concepts, commerce, finance, a fashion extension, one customer's differences, and the bindings to two
databases). Nothing on them is drawn by hand: the modules, the compiled queries, the rows from both backends, the
decision with its evidence and the reach of a column change are what the library computed for that example.

`xds serve` turns the same screens into a working page: plug modules in and out, edit any module as its file,
run a query in eight languages or write one in SPARQL or Cypher yourself, decide, file an agent's request and
approve it, run the questions and the database check. A flow tab shows every stage (source, definition, database
check, projection, queries, decisions, questions) with what it holds now, a data tab drafts a studio from uploaded
files (see [Start from your own data](#start-from-your-own-data)), and a guide tab explains each screen, beside a
demo video when `--video` gives one. Every visitor gets a studio of their own, built from the
same studio file, so nothing one person does reaches another; with `--users`, a team signs in and shares one studio
(see [A team studio](#a-team-studio)).

<p align="center">
  <img src="assets/screens/library.png" alt="Ontology library screen: every domain package with its kind, version, requirements and an on/off switch for this studio, the layers plugged in now, and what unplugging a module would take away" width="920">
</p>

<p align="center"><b>The ontology library.</b> Commerce, finance and every other domain live as separate, versioned packages;
a studio plugs in the ones it needs, and the screen shows what unplugging one would take away before it happens.</p>

<table>
  <tr>
    <td width="50%"><img src="assets/screens/ontology.png" alt="Ontology screen: schema graph coloured by the module each type comes from, domain types hanging under common concepts, and the selected type's properties with their columns and modules"></td>
    <td width="50%"><img src="assets/screens/query.png" alt="Query screen: one ontology query, its text in eight backend languages, and identical rows from the SQL source and the SPARQL graph"></td>
  </tr>
  <tr>
    <td><b>Ontology.</b> Every type coloured by the module it comes from; domain types hang under common concepts (customer and borrower under party, order and loan under agreement); each property shows its column and module, each type its standard alignments.</td>
    <td><b>One query, every language.</b> The ontology query, its text for PostgreSQL, MySQL, Oracle, Cypher 25, GQL, SPARQL, SQL/PGQ and Gremlin, and the rows from each backend side by side.</td>
  </tr>
  <tr>
    <td><img src="assets/screens/decision.png" alt="Decision screen: the decision table with the rule that fired, the evidence path to source columns, and an action request waiting for a person's approval"></td>
    <td><img src="assets/screens/map.png" alt="Data map screen: everything that depends on one column, what an agent can reach, and the data nobody uses"></td>
  </tr>
  <tr>
    <td><b>Decide and act.</b> A decision table (here with the customer's own VIP rule plugged in ahead of the standard ones, each rule citing its policy), the source column behind every input, and an agent's action request waiting for a person.</td>
    <td><b>The data map.</b> What a column change touches, from property to agent; what one agent can reach; what nobody uses.</td>
  </tr>
</table>

## The pieces

| Module | What it does |
|---|---|
| `model` · `validate` | The definition: object types (key, table, properties with type, enum values and column), links (`on` a join or `via` a link table; cardinality, inverse, transitive, symmetric, required), interfaces, state machines, decision tables, actions, roles with row filters, registered queries and validation questions. JSON or YAML, checked for consistency before anything runs |
| `expr` | Computed properties: arithmetic, comparisons and functions over an object's properties, aggregates along links (`sum(hasItem.line_total)`) and the latest or earliest value of a series, typed and checked, compiled into SQL, SPARQL and Cypher (GQL and SQL/PGQ take the ones without links and dates) |
| `modules` · `library` | Domain knowledge as packages: common concepts, domains, industry extensions, one customer's differences and the bindings to a database, each versioned and kept apart in a library, composed in requirement order with the origin of every element recorded, plugged in and out at run time and swapped for an edited version; an overlay holds modules in memory over a library folder |
| `draft` · `induce` · `mapping` | Files (CSV, TSV, Excel) and databases (SQLite, PostgreSQL) read into a drafted definition and its bindings: objects, keys, types, allowed values, relations, state machines from a history table, actions, roles, questions and queries, each with its reason; a decision table drawn from past outcomes; or the tables bound onto a standard module instead of becoming new types |
| `review` | The flow's stages and pass conditions, agreement with past decisions, and change requests: a new module version tried on a copy of the studio, reviewed against the conditions, approved by another person, saved as a version |
| `identity` | Records that several systems keep under their own keys, joined by match rules into one object with a crosswalk, with the evidence for every join |
| `bindings` | The definition checked against the actual database: tables and columns, types, duplicate keys, missing required values, enum values the definition does not know, links that point at nothing |
| `ir` · `check` | The ontology query: a typed graph pattern with filters, `exists`, multi-hop links, aggregates, order and parameters. The check resolves link direction (inverse names included), types every literal and parameter, and explains what is wrong in plain sentences |
| `compile` | One compiler per language: SQL (PostgreSQL and SQLite natively, every other dialect through sqlglot), Cypher 25, ISO GQL, SPARQL 1.1, SQL/PGQ, and the `CREATE PROPERTY GRAPH` for the bound tables. Literals are always bound as parameters; NULLs sort last everywhere |
| `parse` | SPARQL and Cypher read back into the IR, so a query in either runs on any backend |
| `backends` | SQLite, any DB-API connection, rdflib, any SPARQL 1.1 endpoint, Neo4j, Gremlin Server, and a callable adapter for engines without a driver here. Each declares what it can do |
| `projection` | Source rows to RDF triples or property-graph nodes and edges, and the change set between two projections for incremental loads |
| `decide` · `actions` · `roles` | Decision tables with evidence, exported to GoRules JDM and run on ZEN; actions with checked parameter values, human approval, write-back, an external request to allowed hosts, rollback and an audit trail; role scoping of every query and tool, with masked properties |
| `reason` | Inverse, symmetric and transitive links derived with their reasons; shape checks; SHACL generated and validated; OWL 2 RL materialization |
| `exchange` | OWL and R2RML export with a report of what each format cannot hold; OWL/RDFS import as a starting definition |
| `catalog` | The data space as a graph: databases, tables, columns, files, collections, ontology objects, queries, decisions, actions, roles, agents |
| `nl` | A schema card and IR guide for a language model, and a loop that checks its answer and asks again with the issues |
| `conformance` · `studio` · `cli` · `mcp_server` · `preview` | Runs across backends compared row for row; the facade; the `xds` command; the MCP server; the studio page as a file |
| `web` | The studio page served over HTTP with the standard library only: flow with its pass conditions, file upload, the draft and standard bindings, library with the module editor and change review, ontology graph, queries, decisions, approvals and rollback, checks, and the guide with its video; one studio per visitor, or one per team behind a sign-in |

## Define once

```yaml
objects:
  OrderItem:
    label: 주문상품
    source: {table: order_items}
    key: item_id
    properties:
      delivered_at: {type: datetime, label: 배송 완료 일시}
      item_status:  {type: enum, values: [NORMAL, RETURN_REQUESTED, RETURNED]}
    states: {property: item_status, initial: NORMAL, transitions: [{from: NORMAL, to: RETURN_REQUESTED}]}
links:
  hasItem: {from: Order, to: OrderItem, cardinality: one_to_many, on: {order_id: order_id}, inverse: itemOf}
decisions:
  returnEligibility:
    target: OrderItem
    inputs:
      days_since_delivery: {type: integer, days_since: delivered_at}
      category_returnable: {type: boolean, path: [ofSku, skuOf, inCategory], property: returnable}
    outputs: {eligible: boolean, reason: string}
    rules:
      - {when: {days_since_delivery: "null"}, then: {eligible: false, reason: 배송 완료 전입니다}}
      - {when: {category_returnable: "false"}, then: {eligible: false, reason: 반품할 수 없는 카테고리입니다}}
      - {when: {days_since_delivery: "<= 7"}, then: {eligible: true, reason: 반품기간 7일 이내입니다}}
roles:
  customer_agent:
    read: [Order, OrderItem]
    row_filters:
      Order: {eq: [$self.customer_id, {principal: customer_id}]}
```

The full example is [`examples/commerce/ontology.yaml`](examples/commerce/ontology.yaml): eight object types
(one of them a price history), nine links, eight computed properties, a decision, an action, three roles, twelve
registered queries and seven validation questions.
Decision cells are a small FEEL subset: `-`, `null`, `not null`, `<= 7`, `[1..7]`, `"VIP"`, `!= "NORMAL"`,
`in ["A", "B"]`, `true`.

## Computed properties and series

```yaml
OrderItem:
  properties:
    line_total: {type: decimal, expr: "unit_price * quantity"}
Order:
  properties:
    total:  {type: decimal, expr: "coalesce(sum(hasItem.line_total), 0)"}
    billed: {type: decimal, expr: "if(status = 'CANCELLED', 0, total)"}
PriceChange:
  series: {time: changed_at, of: priceOf}        # observations over time
Sku:
  properties:
    last_price: {type: decimal, expr: "latest(priceChanges.price)"}
```

A computed property is asked for like any other (`o.total`, in IR, SPARQL or Cypher) and compiled into each
language: a scalar subquery in SQL, `BIND` and a grouped subquery in SPARQL, a pattern comprehension in Cypher. It is
never copied into a graph, so the conformance run compares the expression itself across backends. Nulls follow one
rule everywhere (division by zero and an `if` on a null condition give null). Functions: `coalesce`, `if`, `abs`,
`round`, `floor`, `ceil`, `lower`, `upper`, `length`, `concat`, `year`, `month`, `day`, `days_between`; aggregates
along a link path: `sum`, `avg`, `min`, `max`, `count`, and `latest` / `earliest` on a series. A language that has no
form for one says so before it runs.

## Plug domains in and out

Domain knowledge comes and goes, so it is packaged. A library keeps each package apart as
`<name>/<version>.yaml`; a studio composes the ones it needs.

| Kind | Example | What it holds |
|---|---|---|
| `core` | `core` (공통 개념) | Concepts every domain hangs from: party, agreement, the `Named` interface |
| `domain` | `commerce`, `finance` | The standard definition of a domain, aligned to schema.org, GS1 or FIBO, with no tables in it |
| `industry` | `fashion`, `food` | What one industry adds on top of the standard: material and season, expiry and storage |
| `customer` | `acme-overlay` | Only what one customer does differently: an extra property, a VIP rule placed ahead of the standard ones, a query taken out |
| `binding` | `commerce-bindings` | The tables and columns of one database. Swap it, and the same definition reads another system |
| `quality` | `return-quality` | How a definition is checked: validation questions and the flow's pass conditions. Attached, it raises the studio's conditions where it asks more; detached, they go back |
| `method` | `build-rules` | How a draft is built from data: the draft rules (allowed-value limits, key, state and person hints) the data tab starts from |

```yaml
module: acme-overlay
kind: customer
requires: [commerce, commerce-bindings]
extend:
  objects:
    OrderItem: {properties: {gift_wrap: {type: boolean, label: 선물 포장}}}
  decisions:
    returnEligibility:
      inputs: {customer_grade: {type: string, path: [itemOf, placedBy], property: grade}}
      rules_prepend:
        - {id: vip-window, when: {customer_grade: '"VIP"', days_since_delivery: "<= 14"},
           then: {eligible: true, reason: VIP 고객은 14일까지 반품할 수 있습니다}, cite: ACME 운영 정책 4.1}
remove: {queries: [wishlistCount]}
```

```python
from xgen_data_studio.library import Library
lib = Library("examples/library")
studio = Studio.from_library(lib, ["commerce-bindings", "fashion", "acme-overlay", "finance-bindings"])  # + requirements
db = studio.add_backend("source", SqliteBackend())
for seed in ("examples/commerce/seed.sql", "examples/library/seed_finance.sql"):
    db.script(open(seed, encoding="utf-8").read())

studio.composition.owner("property:OrderItem.gift_wrap")     # 'acme-overlay': every element knows its module
studio.detach_impact("fashion").removed                      # what would go, before anything goes
studio.detach("acme-overlay"); studio.attach("acme-overlay") # the VIP rule leaves and comes back
studio.detach("commerce")                                    # refused: three modules depend on it (cascade=True to take them too)
studio.run("allParties")                                     # one concept, two domains: customers and borrowers
studio.check_bindings()                                      # the definition against the actual database
```

A concept with no table of its own is asked through its subtypes: in SQL as the `UNION ALL` of their tables,
in SPARQL and Cypher through the concept's type or label, and the conformance run checks the answers agree.
`aligned` IRIs export as `skos:exactMatch`, `cite` as `dcterms:source`, the module as `rdfs:isDefinedBy`; an
imported standard keeps its original IRIs as alignments.

## Start from your own data

A definition does not have to be written first. `xds draft` reads files or a database and drafts the two
modules a library expects, a definition and its bindings, keeping the reason for every choice:

| | How it is decided |
|---|---|
| Objects | One per table, after the W3C Direct Mapping; a table of two relation columns and nothing else becomes a many-to-many link instead |
| Keys | The declared primary key; for files, a column whose values are all present and distinct (a row number when none is) |
| Types | A database's declared types (ISO text in SQLite is read as dates); for files, the values: integers with or without thousands separators, decimals, dates, date-times, booleans. Values with leading zeros stay text, as codes |
| Allowed values | Text columns whose few values repeat |
| Relations | Declared foreign keys; otherwise a column named after another table's key (the same name, `<table>_<key>`, `<table>_id`) whose values are all found among that key's values. A key name many tables share, such as `id`, does not make a relation by its name alone |
| States | A status column (by the state name hints) with allowed values; a table that keeps past states of the same rows gives the transitions in the order they happened and the usual first state, and becomes a series. One action per state things move into |
| Roles | A viewer, an operator when there are actions, and for a person-like table (by the person name hints) a role that reads only one person's rows |
| Queries | A list per object, a count per relation and per allowed value, so a conformance run has something to compare from the start |
| Questions | Each generated query with the rows it gives now, to check later changes against |

```bash
xds draft members.csv books.csv loans.csv -o lib-demo     # lib-demo/library/, data.sqlite, studio.yaml
xds draft --sqlite shop.db --name shop                     # opened read-only; prints the two modules
xds draft --dsn "$XDS_DSN" -o shop                         # the studio file reads ${XDS_DSN}, not the password
xds draft *.csv --rules '{"enum_max": 10, "infer_links": false}' --drop object:Log -o lib-demo
xds serve lib-demo/studio.yaml
```

Nothing in the draft is fixed. The rules above are `DraftRules` (how many distinct values still make a category,
whether relations are inferred, whether link tables become many-to-many links, the name hints for titles, parents
and keys, which queries to generate), and `Draft.revise()` takes a person's edits on top: another key column, a
property's type and allowed values, labels, left-out objects, properties and queries, a relation's cardinality, a
relation added by hand. A type chosen for a file's column is how its values are loaded, and a value that does not
fit is reported with its table, column and value.

On the example commerce database (primary keys declared, foreign keys not) the draft finds the eight relations of
the hand-written commerce ontology, the wishlist table as a many-to-many link included, and every generated query
returns the same rows from SQLite and from the RDF projection. On the page, the data tab does the same for
uploaded CSV and Excel files (and, with `--allow-connect`, a database address): the draft builds step by step with
the reason for each object, key, type and relation, a person sets the rules and edits each step (every edit is
checked again on the spot, and errors hold the draft back), and the draft is plugged into that visitor's studio.
Any module, the example ones and a plugged-in draft alike, opens on the library tab as its file: edit its objects,
decisions, questions or roles, check it, and save it into that visitor's library; a plugged-in module is swapped
in at once (`Studio.replace`). The library folder itself is not written; download the file to keep it.
`examples/files` holds a fictional library's files to try it with.

Two more ways to start. A decision table drawn from past outcomes (`induce.induce`, the page's rules step): a person
picks the column that holds what was decided and the inputs, of the same table or one relation away; each leaf of a
shallow decision tree becomes a rule with how many past cases it covers and gets right, and a five-fold
cross-validation says how well it decides cases it was not drawn from. And bindings onto a standard instead of new
types (`mapping.suggest`, the page's "표준에 연결"): every table and column is scored against the standard's types
and properties (names, labels, aligned vocabulary, romanized Korean, types, allowed values, keys), relations come from
the draft's, and the confirmed matches become a binding module; what the tables do not carry is left out, with the
queries that need it. On the example commerce database it gives the bindings a person wrote, inherited properties
included.

<p align="center">
  <img src="assets/screens/draft.png" alt="Draft screen: the generation steps with their counts, the drafted schema graph, and the relations found in the example files, each with its cardinality, the reason it was inferred and a form to add one by hand" width="920">
</p>

<p align="center"><b>A draft from the six files in <code>examples/files</code>.</b> Each step shows what it found; here the relations, each with the
values that matched and an editable name and cardinality, and the definition check that clears the draft to be plugged in.</p>

## Ask once

```json
{"match": {"o": "Order", "i": "OrderItem"},
 "edges": [["o", "hasItem", "i"]],
 "where": {"and": [{"eq": ["o.status", "DELIVERED"]},
                   {"not_exists": {"match": {"c": "Claim"}, "edges": [["i", "hasClaim", "c"]]}}]},
 "return": ["i.item_id", {"col": "o.order_id", "as": "order"}],
 "order": ["item_id"]}
```

Comparisons `eq ne lt lte gt gte`, `in` / `not_in`, `contains`, `is_null` / `not_null`, `and` / `or` / `not`,
`exists` / `not_exists`; aggregates `count count_distinct sum avg min max`; `{"from": "k", "link": "broader",
"to": "a", "hops": [1, 3]}` for a link from a type to itself; `{"optional": true}` for a left join. A link can be
written in either direction, by its name or its inverse. Named queries live in the definition with their
parameters, so a model or a person can pick one by name.

## Run anywhere

| Language | Backends (examples) | optional | exists | hops | contains | Adapter |
|---|---|---|---|---|---|---|
| SQL | PostgreSQL and SQLite natively; MySQL, Oracle, SQL Server, Snowflake, BigQuery, … through sqlglot | LEFT JOIN | EXISTS | recursive CTE | strpos · instr | `SqliteBackend`, `DbApiBackend` (qmark · format · numeric) |
| Cypher 25 | Neo4j, Memgraph, Neptune openCypher, Apache AGE | OPTIONAL MATCH | `EXISTS {}` | `*1..3` + WITH DISTINCT | CONTAINS | `Neo4jBackend`, loads by UNWIND · MERGE |
| GQL | Spanner Graph, BigQuery Graph, Fabric Graph | OPTIONAL MATCH | `EXISTS {}` | `{1,3}` + ANY | refused | `CallableBackend` around your driver |
| SPARQL 1.1 | rdflib, Fuseki, GraphDB, Stardog, Virtuoso, Oxigraph | OPTIONAL | FILTER EXISTS | path alternatives + DISTINCT | CONTAINS | `RdflibBackend`, `SparqlEndpointBackend` (Graph Store Protocol · Update) |
| SQL/PGQ | Oracle 26ai, Spanner | refused | refused | `{1,3}` | POSITION | `graph_ddl()` writes the property graph over the tables |
| Gremlin 3.8 | Gremlin Server, JanusGraph, Neptune | refused | `where()` | `repeat().emit()` | TextP.containing | `GremlinBackend`, loads a projection with one list binding per script |

A backend declares its `Capabilities`; a query that needs something a backend lacks is refused before it runs,
with the reason. `tests/test_live.py` runs the same studio on live PostgreSQL, Fuseki, Neo4j and Gremlin Server when
their addresses are set (`XDS_LIVE_PG`, `XDS_LIVE_FUSEKI`, `XDS_LIVE_NEO4J`, `XDS_LIVE_GREMLIN`), and the CI runs it
against service containers. Values stay in the source: a graph backend gets a projection only when you ask for one, and
after that only the change set (`DELETE DATA` / `INSERT DATA`, or `MERGE` / `DELETE`).

The same IRIs are used by the SPARQL compiler, the projection and the R2RML export, so an R2RML-aware engine
(Ontop, Stardog, GraphDB) can answer the studio's SPARQL straight from the relational source.

## Decide, act, and stay in scope

```python
r = studio.decide("returnEligibility", "I1001")
r.outputs    # {'eligible': True, 'reason': '배송 완료 후 반품기간 7일 이내입니다'}
r.matched    # ['in-window']
r.evidence   # days_since_delivery = 4 <- order_items.delivered_at, category_returnable = True <- categories.returnable

from xgen_data_studio.actions import Actor
p = studio.actions.request("requestReturn", "I1001", {"reason": "size"}, actor=Actor("bot", "agent", ["customer_agent"]))
p.status     # 'pending': role, parameters, state transition and decision all checked
studio.actions.approve(p.id, approver=Actor("kim", "human", ["operator"]))   # only a person approves
studio.actions.audit                                                       # requested, approved, executed

studio.run("myOrders", role="customer_agent", principal={"customer_id": "C001"})   # only that customer's rows
```

Decision tables export to GoRules JDM (`decide.zen.to_jdm`) and run on the ZEN engine when `use_zen=True`;
the tests check that ZEN and the built-in engine agree on every case.

Actions check what is given (`{type, required, min, max, values, pattern, max_length}` per parameter), and may send
an external request after the change is written, only to hosts the studio file allows (`actions: {call_hosts:
[...]}`); a failed request puts the row back. An executed action can be rolled back, if nothing has changed the row
since, and an action with a request rolls back only when it declares the request that undoes it.

```python
studio.actions.rollback(p.id, actor=Actor("kim", "human", ["operator"]))      # the values before, back in place
studio.run("customerValue", {"least": 0}, role="support_agent").rows[0]       # ('C001', '김하늘', '***-****-0101', ...)
```

A property marked `mask: partial | full` (or listed in a role's `mask`) is shown masked to every role that does not
`unmask` it, and so is a computed property built from it; filtering or ordering on a masked property is refused,
since the answer would give the value away. Queries the studio runs for itself see values in clear.

## Identity across systems

```yaml
identities:
  Person:
    table: person_identity
    members:
      Customer: {phone: phone, name: name}
      Borrower: {phone: phone, name: name}
    rules:
      - {id: same-phone-name, match: [phone, name], normalize: {phone: digits, name: trim}}
```

`studio.resolve_identity("Person")` joins the records that share every field of a rule (after normalizing), keeps
the evidence for each join, and writes the crosswalk in one transaction: `Person` is then an ordinary object with a
link to each member type, asked for the same way on every backend (`customersWhoBorrow` in the example library finds
the customer who is also a borrower).

## Changes are reviewed before they are approved

A studio file's `flow:` names the stages that run and what each must pass:

```yaml
flow:
  gates:
    bind:   {max_errors: 0}          # the definition against the database
    query:  {min_agree: 1.0}         # every registered query answers the same on every backend
    decide: {min_agreement: 0.8}     # past decisions decided again give what was decided then
    check:  {min_accuracy: 0.9, min_grounded: 1.0}   # validation questions: right, and grounded
  agreement:
    decision: returnEligibility
    query: pastReturnCases           # one row per past case, with the values it had then
    inputs: {days_since_delivery: days_after_delivery, item_status: status_then}
    expect: {eligible: approved}
```

`studio.agreement()` decides every past case again and lists the ones that differ, with the rule that fired.
A question's answer is grounded when it carries its condition (the rule that matched, or the query), its source
(the rule's `cite` or its table's, the source column of each value) and the version of the module that answered;
`studio.questions().grounded` is the share, and each ungrounded answer says what it lacks. A `quality` module brings
its own `flow: {gates}`; attached, it holds the studio to whichever of the two asks more.
A change is a new version of one module: `studio.changes.propose(module, by="kim")` tries it on a copy of the
studio (the same source, a fresh graph) and records what it adds, removes and changes, the database check, the
conformance run, the questions and the agreement; `approve(id, by="lee")` refuses a change that does not pass the
flow or that its own author approves, then saves the version to the library and swaps it in. On the page, saving a
module files a change request and shows its review; `xds review studio.yaml module.yaml` prints the same review.

## A team studio

```bash
xds users add users.yaml kim --name 김하람 --roles editor,approver    # the password from XDS_PASSWORD, or asked
xds serve studio.yaml --users users.yaml --library-write --sync 60
```

With `--users`, people sign in (PBKDF2 hashes, a session cookie that is HttpOnly and SameSite=Strict, writes only
from the page itself, sign-in attempts limited) and share one studio. viewer reads and asks, editor changes data and
modules and files requests, approver approves changes and actions, admin also sets the flow. `--library-write` saves
approved versions to the library folder; `--sync` reads the source again every N seconds and sends each graph the
change set.

## Reason, validate, exchange

| Need | Call | Result |
|---|---|---|
| Derived links | `reason.rules.run_rules(onto, projection)` | inverse, symmetric and transitive (depth-capped) links, each with the facts it came from; findings for missing required links, cardinality, exclusive links, required properties, enum values, states |
| Shape validation | `reason.shacl.to_shacl(onto)`, `validate(onto, projection)` | SHACL shapes from the definition, checked with pySHACL |
| OWL reasoning | `reason.owl_rl.materialize(onto, projection)` | owlrl closure; tested to derive exactly what the built-in rules derive |
| Standards out | `exchange.owl.to_owl(onto)`, `exchange.r2rml.to_r2rml(onto)` | OWL 2 and R2RML, with a report of what was preserved, adjusted or left out |
| Standards in | `exchange.importer.from_owl(ttl)` | a starting definition from FIBO, schema.org, GS1 or any OWL/RDFS, with the same report |

## The data map

```python
from xgen_data_studio.catalog import from_ontology
cat = from_ontology(studio.onto)                  # tables, columns, objects, properties, queries, decisions, roles
cat.add_file("policies/returns.pdf", folder="policies", collection="commerce-policies")
cat.add_agent("support", roles=["customer_agent"], uses=["collection:commerce-policies"])
cat.impact("column:order_items.delivered_at")     # the property, query, decision, action, role and agent it reaches
cat.sees("support")                               # every table, column and file that agent can reach
cat.unused()                                      # what no agent or workflow uses
```

## Questions in plain language

`nl.IRGenerator(onto, llm)` gives a model a schema card (only what the role may read) and the IR format, and
takes back either an IR object or a registered query name with parameters. The answer is checked against the
ontology; if it fails, the model is asked again with the list of issues. The model never writes backend
query text. `llm` is any `(system, prompt) -> str`; `nl.openai_chat(url, model)` makes one for any
OpenAI-compatible endpoint, and `xds serve --llm-url ... --llm-model ...` adds a question box to the page. An answer
that checks but finds no rows goes back once with sample values of the properties it compared (only what the role
may read in clear). `xds nl-eval studio.yaml questions.yaml --llm-url ... --llm-model ...` scores a model on your
own questions by execution: the gold query's rows must be in the answer's;
[`examples/commerce/nl_questions.yaml`](examples/commerce/nl_questions.yaml) has sixteen.

## Rules from policy text

`policy.PolicyDrafter(modules, llm).draft(text, target="OrderItem")` gives a model the same schema card, the
decision table format and the policy's clauses, and takes back one decision table. The engine checks it as a module
(inputs it can read from the target or along a path, tests it can evaluate, outputs the rules set) and checks that
every rule cites a clause the text numbers; whatever is wrong goes back to the model. The draft is a module of its
own, and a person files it as a change request, so it is tried on a copy and approved before it decides anything.
On the page, `xds serve --llm-url ... --policies examples/policies` adds "정책서로 규칙 초안" to the library; the
command is `xds policy-draft studio.yaml policy.md --target OrderItem --llm-url ... --llm-model ...`.
[`examples/policies/교환정책서.md`](examples/policies/교환정책서.md) is a made-up exchange policy.

## Agents over MCP

```bash
xds mcp examples/commerce/studio.yaml --role customer_agent --principal customer_id=C001 [--read-only]
```

Tools: `describe_ontology`, `list_modules`, `list_backends`, `translate_query`, `run_query`, `run_sparql`, `run_cypher`,
`decide`, `request_action`, `list_proposals`. Every call runs inside the role's row filters; `request_action`
only files a request, and nothing is written until a person approves it. Works with the MCP Python SDK 1.x and 2.x.

## Install

```bash
pip install xgen-data-studio                 # core, zero deps: SQLite, JSON, the IR, every compiler, decisions, rules
pip install "xgen-data-studio[all]"          # + PyYAML, rdflib, sqlglot, pySHACL, owlrl, ZEN, MCP
pip install "xgen-data-studio[postgres]"     # + psycopg      ("[neo4j]" for the Neo4j driver)
pip install "xgen-data-studio[xlsx]"         # + openpyxl, for drafting from Excel workbooks
pip install "xgen-data-studio[gremlin]"      # + gremlinpython, for Gremlin Server
```

Run the demo from a checkout with only PyYAML and rdflib installed:

```bash
python examples/commerce/demo.py
```

## Command line

```bash
xds validate examples/commerce/ontology.yaml
xds translate examples/commerce/ontology.yaml lowStock --to sql:snowflake --param threshold=5
xds translate examples/commerce/ontology.yaml "MATCH (o:Order) RETURN o.status, count(o) AS n" --from cypher --to sparql
xds export examples/commerce/ontology.yaml --format owl         # shacl · r2rml · pgq · jdm · json · yaml · report
xds import-owl vocabulary.ttl -o ontology.yaml
xds run examples/commerce/studio.yaml myOrders --role customer_agent --principal customer_id=C001
xds sparql examples/commerce/studio.yaml query.rq --backend source
xds decide examples/commerce/studio.yaml returnEligibility I1001
xds questions examples/commerce/studio.yaml                    # validation questions and accuracy
xds conformance examples/commerce/studio.yaml                  # every registered query on every backend
xds preview examples/library/studio.yaml -o studio.html        # the page in the screenshots
xds serve examples/library/studio.yaml --port 7710             # the same page, working: one studio per visitor
xds serve examples/library/studio.yaml --samples examples/files  # + example files a visitor loads with one click
xds serve examples/library/studio.yaml --video demo.mp4          # + a demo video beside the guide (demo.chapters.json)
xds serve examples/library/studio.yaml --allow-connect --file-kb 4096 --rows 50000  # inside your own network only
xds draft examples/files/*.csv -o lib-demo                     # a definition and bindings drafted from data
xds gates examples/library/studio.yaml                         # the flow's pass conditions, measured
xds agreement examples/library/studio.yaml                     # past decisions decided again
xds review examples/library/studio.yaml acme-1.1.0.yaml        # a new module version, reviewed on a copy
xds identity examples/library/studio.yaml Person --write       # join the records, write the crosswalk
xds sync examples/library/studio.yaml --every 60               # the graphs kept up with the source
xds nl-eval examples/commerce/studio.yaml examples/commerce/nl_questions.yaml --llm-url ... --llm-model ...
xds policy-draft examples/library/studio.yaml examples/policies/교환정책서.md --target OrderItem --llm-url ... --llm-model ...
xds users add users.yaml kim --roles editor                    # a person of a team studio (xds serve --users)
xds library list examples/library                              # every package, its kind, versions and requirements
xds library create my-lib energy --kind domain --label "에너지 설비" --requires core
xds library import-owl my-lib fibo-loans.ttl fibo-loans --requires core
xds library diff my-lib fashion 1.0.0 1.1.0                    # what a new version adds, removes, changes
xds library compose examples/library commerce-bindings finance-bindings -o ontology.yaml
xds modules examples/library/studio.yaml --impact fashion      # what detaching it would take away
xds bindings examples/library/studio.yaml                      # the definition against the database
```

A studio file names the ontology, the backends and what to project at start:

```yaml
ontology: ontology.yaml
backends:
  source: {kind: sqlite, path: commerce.db, source: true}       # postgres (dsn) · dbapi (module, connect)
  graph:  {kind: rdflib}                                         # sparql (query_url, update_url, gsp_url)
  neo:    {kind: neo4j, uri: "bolt://localhost:7687", password: "${NEO4J_PASSWORD}"}
project: [graph]
```

## Design

- **Domains are packages.** Commerce, finance and every later domain are versioned modules in a library; a
  customer's differences and a database's bindings are modules too, so the standard is never edited to fit one site.
- **Domains meet in concepts.** Domain types hang from shared concepts and align to public vocabularies, so a
  question about a concept reaches every domain that specialises it.
- **One definition, many executions.** The definition is the only artifact people edit; SQL, Cypher, GQL,
  SPARQL, SQL/PGQ, OWL, SHACL, R2RML and JDM are all generated from it.
- **Values stay in the source.** Object types are bound to tables; a graph store is a projection you opt into,
  kept current by change sets.
- **A language model writes the IR, never the backend text.** Generated queries are checked against the
  ontology before they run, and every literal is a bound parameter.
- **Rules decide, reasoners derive.** Business decisions live in decision tables with their evidence;
  OWL RL and SHACL derive and validate facts. A decision does not depend on which reasoner is installed.
- **Prove it with the same rows.** Conformance runs compare every registered query across backends, and the
  readers are tested by compiling each query to SPARQL and Cypher and reading it back.
- **`dependencies = []`.** Everything optional is an extra; with all of them blocked the core test suite still passes.

```
src/xgen_data_studio/
  model.py validate.py      # the definition and its checks
  modules.py library.py     # packages, composition, attach / detach; the library of versioned packages
  bindings.py               # the definition against the actual database
  expr.py                   # computed properties: parse, type, render per language
  draft.py induce.py mapping.py   # drafted definitions, decision tables from outcomes, bindings onto a standard
  review.py identity.py     # flow, agreement, change requests; identities and crosswalks
  ir.py check.py values.py  # the query IR, its check, typed values
  compile/                  # sql (+ dialects) · cypher (+ gql) · sparql · pgq · gremlin
  parse/                    # sparql · cypher -> IR
  backends/                 # sql (sqlite, dbapi) · rdf (rdflib, endpoint) · graph (neo4j, callable) · gremlin
  projection.py rdf.py      # rows -> RDF / property graph, change sets; IRIs and Turtle
  decide/ actions.py roles.py
  reason/                   # rules · shacl · owl_rl
  exchange/                 # owl · r2rml · importer
  catalog.py nl.py policy.py conformance.py studio.py config.py tools.py mcp_server.py preview.py cli.py
  web/                      # xds serve: api.py (answers from one studio), server.py, team.py, static/ (the page)
examples/commerce/          # one ontology file, seed data, studio file, demo
examples/library/           # the same domain as packages, plus finance, fashion, food and a customer overlay
examples/files/             # a fictional library's CSV files, for drafting from data
tools/                      # render_screens.py (the README images), architecture.html
```

## Roadmap

- computed properties with filtered aggregates (`sum(hasItem.line_total where ...)`), and in Gremlin and SQL/PGQ
- optional edges in Gremlin; TinkerPop 4 once it is released
- sign-in through an organisation's identity provider for team studios
- decision tables drawn from outcomes with dates as inputs (days between two columns)

## Repository model

[`PlateerLab/xgen-data-studio`](https://github.com/PlateerLab/xgen-data-studio) is the source of truth.
Members of the PlateerLab organization commit there directly; CI runs the full suite on Python 3.10–3.12 and the
core suite with no optional dependencies.

## License

Source-available. Copyright (c) 2026 Jinsoo Kim.

Members of the PlateerLab organization may use, modify and ship it as part of Plateer products (LICENSE §4).
For anyone else, reading and citing are fine; any other use needs written permission. See [`LICENSE`](LICENSE).
