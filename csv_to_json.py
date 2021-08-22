import json
import re
import os.path
import itertools
from abc import ABC
from functools import partial

from unidecode import unidecode

# This is the newest version, use this

ENGLISH = "english"
DINE = "dine"
NAVAJO = "navajo"  # TODO only use dine or navajo, not both
AUDIO_PATH = "/audio"

WORD = "word"
NORMALIZED = "normalized"
VARIANT = "variant"
DEFINITION = "definition"
LITERAL = "literal"
COMMENT = "comment"
SEE_ALSO = "see_also"
SENTENCE = "sentence"
PHONETIC = "phonetic"
AUDIO = "audio"

CSV_DIVIDER = "\t"

AUDIO_FILES_ENG = os.listdir(os.curdir + AUDIO_PATH + "/" + ENGLISH)
AUDIO_FILES_DINE = os.listdir(os.curdir + AUDIO_PATH + "/" + DINE)

ref_pattern = re.compile(r"@(\d)$")
normalization_table = str.maketrans(" ", "-", "'(),.")


def normalize(accented_string):
	return unidecode(accented_string).translate(normalization_table).lower()


class Row:
	def __init__(self, row):
		self.english = {}
		self.navajo = {}
		
		(self.english[WORD],
		 self.english[VARIANT],
		 self.navajo[VARIANT],
		 self.navajo[WORD],
		 self.english[DEFINITION],
		 self.navajo[DEFINITION],
		 self.navajo[LITERAL],
		 self.navajo[COMMENT],
		 self.english[SEE_ALSO],
		 self.navajo[SEE_ALSO],
		 self.english[SENTENCE],
		 self.navajo[SENTENCE],
		 self.english[PHONETIC],
		 self.navajo[PHONETIC],
		 audio_eng,
		 audio_dine
		 ) = [x.strip() for x in row]
		
		self.english[NORMALIZED] = normalize(self.english[WORD])
		self.navajo[NORMALIZED] = normalize(self.navajo[WORD])
		
		self.english[AUDIO] = get_audio(ENGLISH, self.english[WORD], audio_eng, AUDIO_FILES_ENG)
		self.navajo[AUDIO] = get_audio(DINE, self.english[WORD], audio_dine, AUDIO_FILES_DINE)
		# note that the dine audio files are named using the english word + "dine"


def keyfunc_eng(r: Row):
	return r.english[NORMALIZED]


def keyfunc_dine(r: Row):
	return r.navajo[NORMALIZED]


def get_audio(lang, word, filename, directory):
	if not filename:
		filename = normalize(word)
	audio_path = filename + "-" + lang + ".m4a"
	if audio_path in directory:
		return "/".join([AUDIO_PATH, lang, audio_path])
	return ""
	
def get_english_audio_path(row: Row):
	return get_audio(ENGLISH, row.english[WORD], row.english[AUDIO], AUDIO_FILES_ENG)

def get_dine_audio_path(row: Row):
	return get_audio(DINE, row.english[WORD], row.navajo[AUDIO], AUDIO_FILES_DINE)
	# note that the dine audio files are named using the english word + "dine"


class RawRows:
	def __init__(self):
		self.english = {}
		self.navajo = {}


raw_rows = RawRows()


class SeeAlso:
	def __init__(self):
		self.entries = {}
	
	def add_row(self, row, lang):
		lang_row = getattr(row, lang)
		see_also = lang_row[SEE_ALSO]
		ref_match = ref_pattern.match(see_also)
		if ref_match:
			# it's an @ reference
			see_also = getattr(raw_rows.english[(lang_row[WORD], ref_match.group(1))], lang)[SEE_ALSO]
			
		
		for word in see_also.split(", "):
			if word:
				self.entries[normalize(word)] = word
		
	def add(self, attr):
		return partial(self.add_row, attr)
	
	def has_entries(self):
		return len(self.entries) > 0
	
	def dump(self):
		return [{"word": word, "normalized": normalized} for (normalized, word) in self.entries.items()]
	
	
class Dictionary:
	def __init__(self, lines):
		self.english = {}
		self.navajo = {}
		
		unsorted_rows = [Row(line.strip("\n").split(CSV_DIVIDER)) for line in lines]
		# sort to ensure that we don't reference variants we haven't seen yet
		rows = sorted(unsorted_rows, key=lambda r: normalize(r.english[WORD]) + r.english[VARIANT])
		
		# I think doing something like this and establishing a lookup would make things
		# much easier when trying to get variants
		raw_rows.english = {(row.english[WORD], row.english[VARIANT]): row
		                    for row in sorted(rows, key=keyfunc_eng)}
		raw_rows.navajo = {(row.navajo[WORD], row.navajo[VARIANT]): row
		                   for row in sorted(rows, key=keyfunc_dine)}
		
		# TODO so we don't need to have these
		eng_rows = itertools.groupby(sorted(rows, key=keyfunc_eng), keyfunc_eng)
		navajo_rows = itertools.groupby(sorted(rows, key=keyfunc_dine), keyfunc_dine)
		
		for (eng_key, word_rows) in eng_rows:
			if not eng_key:
				continue
				
			entry = Translation(eng_key, ENGLISH, NAVAJO)
			
			for row in word_rows:
				entry.add(row, NAVAJO)
			self.english[eng_key] = entry
		
		for (navajo_key, word_rows) in navajo_rows:
			if not navajo_key:
				continue
			
			entry = Translation(navajo_key, NAVAJO, ENGLISH)
			
			for row in word_rows:
				entry.add(row, ENGLISH)
			self.navajo[navajo_key] = entry
	
	def dump(self, out):
		english = {k: e.dump() for (k, e) in self.english.items()}
		navajo = {k: e.dump() for (k, e) in self.navajo.items()}
		json.dump({"entries": {"english": english, "navajo": navajo}},
		          out, indent=2, ensure_ascii=False)


class Settable(ABC):
	def __init__(self, lang):
		self.lang = lang
		self.data = {}
			
	def set(self, row, key):
		value = getattr(row, self.lang)[key]
		
		if not value:
			return
		
		try:
			ref_match = ref_pattern.match(value)
			if ref_match:
				# it's an @ reference
				word = row.english[WORD]
				original_row = raw_rows.english[(word, ref_match.group(1))]
				# at the moment the references are always defined from the english side :/
				
				value = getattr(original_row, self.lang)[key]
		except TypeError:
			# it's not a string, actually
			pass
		
		if value:
			self.data[key] = value


class Translation(Settable):
	keys = {}
	t_keys = {}
	sub_keys = {}
	
	def __init__(self, word, from_lang, to_lang):
		super().__init__(from_lang)
		self.word = word
		self.to_lang = to_lang
		self.see_also = SeeAlso()
		self.short_translations = []
		self.translations = {}
		
	def from_row(self, row):
		return getattr(row, self.lang)
	
	def to_row(self, row):
		return getattr(row, self.to_lang)
	
	def add(self, row, to_lang):
		for key in getattr(row, self.lang):
			self.set(row, key)
		
		self.short_translations.append(getattr(row, to_lang)[WORD])
		self.add_translation(row, to_lang)
		self.see_also.add_row(row, self.lang)
	
	def add_translation(self, row, to_lang):
		# definition = getattr(row, self.t_def_key)
		definition = getattr(row, self.lang)[DEFINITION]
		translation = self.translations.setdefault(definition,
		                                           Definition(row, to_lang))
		translation.add(row)
		translation.see_also.add_row(row, to_lang)
	
	def dump(self):
		out = {k: v for (k, v) in self.data.items() if v}
		if VARIANT in out:
			del out[VARIANT]  # we don't need to see this
		out["short_translations"] = self.short_translations
		if self.see_also.has_entries():
			out["see_also"] = self.see_also.dump()
		out["translations"] = [t.dump() for t in self.translations.values()]
		return out


class Definition(Settable):
	def __init__(self, row, lang):
		super().__init__(lang)
		self.see_also = SeeAlso()
		self.entries = []
		self.set(row, DEFINITION)  # yeah only the one key
		
	
	def add(self, row):
		self.entries.append(DefinitionEntry(row, self.lang))
	
	def dump(self):
		out = {k: v for (k, v) in self.data.items() if v}
		if self.see_also.has_entries():
			out["see_also"] = self.see_also.dump()
		out["entries"] = [e.dump() for e in self.entries]
		return out
	
	
class DefinitionEntry(Settable):
	def __init__(self, row, lang):
		super().__init__(lang)
		self.data = {}
		for key in getattr(row, lang):
			if not key == DEFINITION:
				self.set(row, key)
	
	def dump(self):
		return {k: v for (k, v) in self.data.items() if v}


def main():
	with open("translation.tsv", encoding='utf-8') as csv:
		header_row, *rest = csv
		dictionary = Dictionary(rest)
	
	with open("translation.json", "w", encoding='utf-8') as out:
		dictionary.dump(out)


if __name__ == "__main__":
	main()
