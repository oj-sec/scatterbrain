export function parseCSV(fileString) {
    let rows = [];
    let currentRow = [];
    let insideQuotes = false;
    let buffer = "";

    for (let i = 0; i < fileString.length; i++) {
        let char = fileString[i];

        if (insideQuotes) {
            if (char === '"' && fileString[i + 1] === '"') {
                buffer += '"';
                i++;
            } else if (char === '"') {
                insideQuotes = false;
            } else {
                buffer += char;
            }
        } else {
            if (char === '"') {
                insideQuotes = true;
            } else if (char === ",") {
                currentRow.push(buffer.trim());
                buffer = "";
            } else if (char === "\n" || i === fileString.length - 1) {
                if (i === fileString.length - 1) {
                    buffer += char;
                }
                currentRow.push(buffer.trim());
                rows.push(currentRow);
                currentRow = [];
                buffer = "";
            } else {
                buffer += char;
            }
        }
    }
    return rows;
}