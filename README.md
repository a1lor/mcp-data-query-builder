<div align="center">
  <h1>🚀 MCP Data Query Builder</h1>
  <p><strong>An advanced Model Context Protocol (MCP) server for dynamically querying and analyzing structured data via AI agents.</strong></p>
</div>

---

## 📖 Overview

The **Data Query Builder** is a powerful MCP server designed to grant Large Language Models (LLMs) the ability to seamlessly parse, investigate, and run analytical queries over CSV data. By leveraging a transient, in-memory SQLite database, it enables models to explore data schemas and execute read-only SQL queries completely safely, turning any model into an instant Data Engineer.

Built using `FastMCP`, this server provides a lightweight, secure environment for data analysis tasks.

### ✨ Key Features

- 📂 **Dynamic CSV Loading**: Instruct the agent to load local CSV files into an ephemeral, structured SQL database.
- 🔍 **Schema Exploration**: Tools to probe available tables, introspect column types, and evaluate data depth.
- 🛡️ **Safe Queries (Read-Only)**: Secure command execution that blocks mutating commands (`DROP`, `DELETE`, `UPDATE`, etc.) while allowing unlimited analytical power (`SELECT`, `JOIN`, `GROUP BY`).
- 📊 **Quick Statistics**: Out-of-the-box analytical features (min, max, mean, count) for instantaneous insights without writing full queries.

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10+
- The `fastmcp` package
- An MCP-compatible client (e.g. Claude Desktop, Gemini CLI)

### Quick Start

1. **Clone the repository** (if you haven't already)
2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Server

Start the server using FastMCP:

```bash
mcp dev server.py
# or standard run:
mcp run server.py
```

The server exposes its I/O via `stdio` and can seamlessly plug into your AI ecosystem.

---

## 🤖 AI Action Tools

When configured, the following tools will be available for the AI to orchestrate:

| Tool                 | Arguments                            | Description                                                                                      |
| -------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------ |
| `load_csv`           | `file_path`, `table_name`            | Reads a CSV file from disk and hydrates it into a new SQLite table.                              |
| `list_tables`        | *(none)*                             | Discover loaded tables and their respective row counts.                                          |
| `describe_schema`    | *(none)*                             | Explore column definitions and constraints for intelligent query building.                       |
| `run_query`          | `sql`                                | Run any complex, **read-only** SQL `SELECT` to aggregate, filter, or join data.                  |
| `get_statistics`     | `table_name`, `column`               | Instantly calculate statistical summaries (`min`, `max`, `avg`, `count`) for a specific column.  |

> 💡 **Pro-Tip for Prompts**: *Always ask the AI to run `describe_schema` immediately after `load_csv` so it knows exactly what to query!*

<div align="center">
  <i>Part of an advanced curriculum in AI infrastructure and Agentic Modeling.</i>
</div>
