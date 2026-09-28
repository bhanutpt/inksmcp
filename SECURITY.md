# Security

## What the server can do

inksmcp runs locally over stdio with the permissions of the user who started it. Through its tools, the
connected assistant can:

- read any SVG, image, JSON or CSV file the user can read (`document_open`, `import_file`,
  `elements_path`, `rows_path`, image `href`), and write files wherever the user can write (`export`,
  `document_save`);
- run Inkscape on those documents. `run_actions` passes actions to Inkscape's shell. It blocks
  file, export, window, dialog, app and quit actions, but other actions can run, including Inkscape's
  bundled extensions (Python scripts that ship with Inkscape).

It makes no network requests. Remote URLs are not fetched, and image links are local files or data URIs.

Treat it like any tool that gives an assistant file access: approve its calls in your client when the
files involved matter, and don't run it with elevated privileges.

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub's
[private vulnerability reporting](https://github.com/bhanutpt/inksmcp/security/advisories/new), not in a
public issue. You can expect a first answer within a week. Fixes are released as a patch version with a
note in the changelog.
