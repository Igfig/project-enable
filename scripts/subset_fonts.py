from fontTools import subset
import os

fonts_path = "assets/fonts/"

flavors = ("woff", "woff2")

def make_subset(font_name, ext="ttf"):
	args = [
		f"{fonts_path}original/{font_name}.ttf",
		"--unicodes=0000-007F",
		"--text=–ʼîïñáąą́éęę́íįį́óǫǫ́ÁĄĄ́ÉĘĘ́ÍĮĮ́ÓǪǪ́łńŁŃ",
		f"--output-file={fonts_path}{font_name}.{ext}"
	]
	
	if ext in flavors:
		args.append("--flavor=" + ext)
	
	subset.main(args)


def main():
	fonts = os.listdir(fonts_path + "original")
	
	for font_file in fonts:
		font_name = font_file.removesuffix(".ttf")
		print(font_name)
		
		make_subset(font_name)
		for flavor in flavors:
			make_subset(font_name, flavor)


main()