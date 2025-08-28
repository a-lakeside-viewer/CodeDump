<%*
const file = app.workspace.getActiveFile();
const content = await app.vault.read(file);

// Extract current frontmatter
const match = content.match(/^---\n([\s\S]*?)\n---/);
if (!match) {
    new Notice("No frontmatter found!");
    return;
}

const yamlText = match[1];
const body = content.slice(match[0].length); // no trim

// Parse YAML properly using a basic parser
function parseYaml(yaml) {
    const lines = yaml.split('\n');
    const obj = {};
    let currentKey = null;

    for (let line of lines) {
        if (/^\s*-\s*/.test(line)) {
            // it's a list item
            if (currentKey && !Array.isArray(obj[currentKey])) {
                obj[currentKey] = [];
            }
            obj[currentKey].push(line.replace(/^\s*-\s*/, '').trim());
        } else {
            const [key, ...rest] = line.split(':');
            currentKey = key.trim();
            obj[currentKey] = rest.join(':').trim();
        }
    }
    return obj;
}

// Improved serializer
function serializeYaml(obj) {
    return Object.entries(obj).map(([key, value]) => {
        if (Array.isArray(value)) {
            return `${key}:\n` + value.map(v => {
                const alreadyQuoted = /^['"](.+)['"]$/.test(v);
                const needsQuotes = /[:#@{}\[\],&*?]|^\s|\s$/.test(v);
                return `  - ${(needsQuotes && !alreadyQuoted) ? `"${v}"` : v}`;
            }).join('\n');
        } else {
            const alreadyQuoted = /^['"](.+)['"]$/.test(value);
            const needsQuotes = /[:#@{}\[\],&*?]|^\s|\s$/.test(value);
            return `${key}: ${(needsQuotes && !alreadyQuoted) ? `"${value}"` : value}`;
        }
    }).join('\n');
}

// Parse and update
let frontmatter = parseYaml(yamlText);

// Update only the fields you care about
frontmatter["unit-location"] = "Quality Control Engineer";
frontmatter["unit-status"] = "For QAS 👁️";
frontmatter["to-do"] = "Await unit's return 🧘🏽";
const modelVal = frontmatter["model"] || "unknown";
frontmatter["tags"] = [`#${modelVal}/qas`];
frontmatter["icon"] = "👁️";

// Rebuild frontmatter
const newFrontmatter = `---\n${serializeYaml(frontmatter)}\n---`;

// Combine with body
const newContent = `${newFrontmatter}${body.startsWith('\n') ? '' : '\n'}${body}`;
await app.vault.modify(file, newContent);

if (tp.config.run_mode === 'inline') tR = '';
%>