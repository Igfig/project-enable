import itertools
import os
import pprint
import fnmatch
import shutil

pp = pprint.PrettyPrinter(indent=4)

out_dir = "out"
exclude_dirs = [".git", ".idea", "__pycache__", "fontawesome-free-5.15.1-web", "old", out_dir,
                "backup", "scripts", "templates"]
exclude_files = ["notes.txt", "translation.json", ".gitignore", "*.scss", "*.pug", "*.zip",
                 "*.lnk", "*.ini", "*.iml", "*.csv", "*.tsv"]


def join_path(*args):
	return os.path.normpath(os.path.join(*args))


os.chdir("..")
print("Working in", os.getcwd())
if os.path.isdir(out_dir):
	shutil.rmtree(out_dir)
os.mkdir(out_dir)

for root, dirs, files in os.walk(".", topdown=True):
	dirs[:] = [d for d in dirs if d not in exclude_dirs]
	
	files_to_exclude = set(itertools.chain.from_iterable(fnmatch.filter(files, ef)
	                                                     for ef in exclude_files))
	files_to_keep = set(files) - files_to_exclude
	
	if files_to_keep:
		out_subdir = join_path(out_dir, root)
		os.makedirs(out_subdir, mode=711, exist_ok=True)
		
		for ftk in files_to_keep:
			shutil.copyfile(join_path(root, ftk), join_path(out_subdir, ftk))
			