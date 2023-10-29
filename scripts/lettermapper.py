import re

# TODO redo this in js
# TODO make it so you can precede special characters with a \ to keep them from being converted

mapping = {
	'1': 'á',
	'2': 'ą',
	'3': 'ą́',
	'4': 'é',
	'5': 'ę',
	'6': 'ę́',
	'7': 'í',
	'8': 'į',
	'9': 'į́',
	'0': 'ó',
	'-': 'ǫ',
	'=': 'ǫ́',
	'!': 'Á',
	'@': 'Ą',
	'#': 'Ą́',
	'$': 'É',
	'%': 'Ę',
	'^': 'Ę́',
	'&': 'Í',
	'*': 'Į',
	# '(': 'Į́', # these two letters never show up in the word list, but parens often do
	# ')': 'Ó',
	'_': 'Ǫ',
	'+': 'Ǫ́',
	'[': 'ł',
	']': 'ń',
	'{': 'Ł',
	'}': 'Ń'
}
dine_chars = mapping.values()

table = str.maketrans(mapping)

skip_columns = [0, 1, 2, 4, 6, 7, 8, 9, 10]

def translate_cell(cell, cells):
	if cells.index(cell) in skip_columns:
		# this is a column that we shouldn't translate
		return cell
	
	if not set(cell).isdisjoint(dine_chars):
		# this cell is already translated
		return cell
	
	if re.match("^[\d@]*$", cell):
		# this cell is just numeric (or has an @ symbol, which is used as an indicator)
		return cell
	
	translated = cell.translate(table)
	repunctuated = re.sub(r"\bĮ́(.+)Ó\b", r"(\1)", translated)
	return repunctuated

def translate_line(line):
	split = line.split("\t")
	translated = [translate_cell(c, split) for c in split]
	return "\t".join(translated)

def main():
	with open("./tomap.csv", encoding='utf-8') as csv:
		translated = [translate_line(line) for line in csv]
		
	with open("./mapped.csv", "w", encoding='utf-8') as out:
		for t in translated:
			print(t, end="")
			out.write(t)


if __name__ == "__main__":
	main()
