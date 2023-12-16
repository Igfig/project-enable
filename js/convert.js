const pairs = [
	["3", "ą́"],
	["6", "ę́"],
	["9", "į́"],
	["=", "ǫ́"],
	["#", "Ą́"],
	["^", "Ę́"],
	["(", "Į́"],
	["+", "Ǫ́"],
	// the letters with both aigu and cedilla are actually two characters, so they'd match on the letter with just the cedilla if that came first. We put the compound characters first to prevent this.
	["1", "á"],
	["2", "ą"],
	["4", "é"],
	["5", "ę"],
	["7", "í"],
	["8", "į"],
	["0", "ó"],
	["-", "ǫ"],
	["[", "ł"],
	["]", "ń"],
	["!", "Á"],
	["@", "Ą"],
	["$", "É"],
	["%", "Ę"],
	["&", "Í"],
	["*", "Į"],
	[")", "Ó"],
	["_", "Ǫ"],
	["{", "Ł"],
	["}", "Ń"]
]

// dicts
const fontToUnicode = Object.fromEntries(pairs)
const unicodeToFont = Object.fromEntries(pairs.map(([a,b]) => [b,a]))

// regexes
const joinKeys = dict => Object
.keys(dict)
.join("|")
.replace(/[.*+?^${}()[\]\\]/g, "\\$&");

const fToURegex = new RegExp(
	"(?<!\\\\)(" +
	joinKeys(fontToUnicode)
	+")",
	"g")

const escapeRegex = new RegExp(
	joinKeys(fontToUnicode),
	"g")

const uToFRegex =  new RegExp(
	joinKeys(unicodeToFont),
	"g")

// handlers
const onRawChange = otherId => event => {
	document.getElementById(otherId).value = event.target.value
	const converted = event.target.value.replaceAll(fToURegex, match => fontToUnicode[match]);
	document.getElementById("unicode").value = converted.replaceAll("\\", "")
}
const onUnicodeChange = event => {
	const escaped = event.target.value.replaceAll(escapeRegex, match => "\\" + match)
	const converted = escaped.replaceAll(uToFRegex, match => unicodeToFont[match])
	document.getElementById("font").value = converted
	document.getElementById("raw").value = converted
}

// events
document.getElementById("font").addEventListener("input", onRawChange("raw"));
document.getElementById("raw").addEventListener("input", onRawChange("font"));

document.getElementById("unicode").addEventListener("input", onUnicodeChange);