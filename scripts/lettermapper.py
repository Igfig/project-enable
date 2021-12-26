import re

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
	'[': 'ł',
	']': 'ń',
	'@': 'Ą',
	'#': 'Ą́',
	'$': 'É',
	'%': 'Ę',
	'^': 'Ę́',
	'&': 'Í',
	'*': 'Į',
	'(': 'Į́',
	')': 'Ó',
	'_': 'Ǫ',
	'+': 'Ǫ́',
	'{': 'Ł',
	'}': 'Ń'
}

table = str.maketrans(mapping)


def main():
	with open("./tomap.csv", encoding='utf-8') as csv:
		translated = [line.translate(table) for line in csv]
		repunctuated = [re.sub(r"\bĮ́(.+)Ó\b", r"(\1)", t) for t in translated]
		
		for t in repunctuated:
			print(t, end="")


if __name__ == "__main__":
	main()
