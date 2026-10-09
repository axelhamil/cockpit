# Standard setups

What a tool should contain to be useful on day one. The user asked for it ("set it up", "what should I put in it"): build it. You are offering it unprompted, after a deployment: one AskUserQuestion, the whole standard recommended. Then show the result in the Browser pane.

The standard is a shape, never a copy. Fit it to this app from `schema.md`, `domain.md` and `codebase.md` before building anything.

## 1. Fit it to the app

Find these in the schema and name them in the user's words. Ask only what the schema cannot tell.

| Role | How to recognise it | Examples |
|---|---|---|
| **Account** | Who pays or owns everything else. An organisation or team table when one exists, the user table otherwise | user, organisation, workspace, shop |
| **Member** | People inside an account, when accounts are organisations | user, seat |
| **Object** | What accounts create with the app, the reason they use it | project, link, invoice, booking, document |
| **Activity** | Rows that prove use, with a date | event, click, session, order, message |
| **Money** | Plan and payment state | subscription, plan, invoice, payment |

- One table can play two roles (a user is Account and Member, an order is Object and Activity): one model, one sheet.
- Two sides (buyers and sellers, hosts and guests): one account sheet per side, linked through the Object they share.
- Money can be two columns on the account (plan, status) and not a table.
- Object unclear: the table accounts write to most. Two candidates: one question.

A role with no table is skipped, and the parts that need it are left out: say which in one sentence. A figure that needs a column the data does not have (an amount, a plan limit, a signup source) is left out the same way, never estimated.

Settle the definitions before the first chart and write them in `domain.md`:

- **Excluded everywhere**: internal and test accounts (ask once for the team's email domain, never guess), banned or deleted accounts, soft-deleted rows, bot traffic.
- **Active**: which activity, over which window. Say when it is an approximation (last session update is not last use).
- **Paying**: which statuses count (usually active and trialing only).
- **Windows**: rolling 30 days and calendar month are different numbers. Pick one per figure and label it.
- **Dates**: a resubscription often keeps the first creation date. A conversion counted on that date lands in the wrong month.
- **Time zone**: the user's, set once in the tool.

Check one figure against something the user already knows (number of customers, last month's revenue) before delivering. A dashboard that is wrong once is not opened again.

## 2. Dashboards and data (Metabase, and Superset, Redash, Lightdash, Grafana)

**Layer first.** One model per role (a saved SQL question when the tool has no models), cleaned once: exclusions applied, columns named in the user's words, technical columns left out, secrets (password hashes, tokens, keys) never selected. Every dashboard reads the models, never the raw tables. An Activity table with many rows gets a second model grouped by day and account for the charts.

**Collections**: `Steering`, `Sheets`, `Explorations` (everything built on request later).

**First pass**, then show it:

- **Finder**: the list of accounts, with one search box on a column that joins name and email. The entry point to every sheet.
- **Account sheet**, a dashboard filtered by one account id: identity, plan and payment state, key counts, Activity over time, its Members, its latest Objects, its last 20 Activity rows.
- **Overview**, with a date filter shared by every chart: the 4 to 6 figures that say how the business is doing, each against the previous period (new accounts, active accounts, paying accounts, revenue when the data holds amounts), one trend per figure, the funnel from signup to first Object to paying.
- **To act on**: lists, not charts. Paying accounts with no Activity for 30 days, accounts that asked to cancel, accounts whose payment failed. Each row opens the account sheet.

Open the account sheet of a real account the user knows, in the Browser pane, and offer the second pass.

**Second pass**, on a yes: an **Object sheet** (what it is, its owner, its Activity), a **Member sheet** when Members exist, **Revenue** when Money exists (paying accounts by plan, new, upgraded and cancelled per month), and **Growth** or **Usage** dashboards only for questions the Overview leaves open.

**Link everything.** This is what makes the setup worth having: from any figure, two clicks reach the people behind it.

- On every table that lists Accounts, Objects or Members, the name column gets a click behaviour: go to a dashboard, the sheet of that role, its id filter fed by the row's id column. Keep the id in the query even when it is not displayed.
- On every sheet, the id filter is connected to each card, on that card's own id column. A card left unconnected shows every account's data: open a real account and check each card.
- The account sheet links to its Objects and Members, and each of those links back to its account.
- The MCP server cannot set a click behaviour or connect a filter: do it in the dashboard's edit mode in the Browser pane.
- Another tool than Metabase: its equivalent, a link that carries the id.

## 3. Automations (n8n, and Activepieces, Windmill, Node-RED)

Propose the ones their data and their channels allow. Ask once where messages should arrive (email, Slack, another chat).

1. **New paying customer**: a message when a subscription starts.
2. **Payment failed or cancellation asked**: a message with the account and its sheet link, so someone can reach out.
3. **Weekly digest**: the Overview figures every Monday morning.
Each workflow reads the SaaS data, never writes to it. A message carries the account's name and the link to its sheet, not its personal data. One that writes outside (sends to customers, calls a paid API) is shown in plain words before it is switched on, as `tools.md` says. Never message the app's customers in bulk: nothing in the database says they agreed to it unless a consent column exists.

## 4. Monitoring (Uptime Kuma, and Gatus, Beszel)

1. The app's home page and its sign-in page.
2. The health address of the API when the code has one (`codebase.md`).
3. Each tool deployed by railway-pilot.
4. Certificate expiry on the app's domain.
5. One notification channel, tested with a real message.
6. A status page, only if the user wants to share one with customers.

Checks every minute for the app, every 5 minutes for the rest.

## 5. Other kinds of tools

| Kind | Examples | Standard |
|---|---|---|
| Visitor analytics | Umami, Plausible, PostHog | The site added, goals for signup and for upgrade, the script added to the app through a pull request (`code-changes.md`) |
| Error tracking | GlitchTip, Sentry | A project per app service, the SDK added through a pull request reviewed by the developer, alerts on new errors only |
| Support | Chatwoot | One inbox, the widget added through a pull request, 5 saved replies drawn from the questions the user says they get |
| Back office | NocoDB, Directus, Appsmith, Budibase | One view per role of section 1, read-only at first. Editing data from a back office skips the app's rules: say it once when they ask for write access |
| Newsletters | Listmonk | Lists from accounts that agreed to receive email only. No consent column means an empty list and a sentence explaining why |

A tool of a kind not listed: find what its own documentation calls a getting started or a recommended setup, fit it with section 1, and note in `proposals.md` what worked.

## 6. After building

- Record as `tools.md` says, and write the definitions settled in section 1 in `domain.md`.
- Open the main screen in the Browser pane and walk the user through it in three sentences.
