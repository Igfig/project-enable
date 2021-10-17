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

AUDIO_PATH = "/audio"
AUDIO_FILES_ENG = os.listdir(os.curdir + AUDIO_PATH + "/" + ENGLISH)
AUDIO_FILES_DINE = os.listdir(os.curdir + AUDIO_PATH + "/" + DINE)

ref_pattern = re.compile(r"@(\d)$")
normalization_table = str.maketrans(" ", "-", "'(),.")


raw_rows = {ENGLISH: {}, DINE: {}}
# this is a global variable. Which isn't ideal, but it makes the Settable interface easier to use.


def normalize(accented_string):
	return unidecode(accented_string).translate(normalization_table).lower()


class Row(dict):
	def __init__(self, row):
		super().__init__({ENGLISH: {}, DINE: {}})
		
		try:
			(self[ENGLISH][WORD],
			 self[ENGLISH][VARIANT],
			 self[DINE][VARIANT],
			 self[DINE][WORD],
			 self[ENGLISH][DEFINITION],
			 self[DINE][DEFINITION],
			 self[DINE][LITERAL],
			 self[DINE][COMMENT],
			 self[ENGLISH][SEE_ALSO],
			 self[DINE][SEE_ALSO],
			 self[ENGLISH][SENTENCE],
			 self[DINE][SENTENCE],
			 self[ENGLISH][PHONETIC],
			 self[DINE][PHONETIC],
			 audio_eng,
			 audio_dine
			 ) = [x.strip() for x in row]
		except ValueError:
			print("failed to parse row:", row)
			return
		
		self[ENGLISH][NORMALIZED] = normalize(self[ENGLISH][WORD])
		self[DINE][NORMALIZED] = normalize(self[DINE][WORD])
		
		self[ENGLISH][AUDIO] = get_audio(ENGLISH, self[ENGLISH][WORD], audio_eng, AUDIO_FILES_ENG)
		self[DINE][AUDIO] = get_audio(DINE, self[ENGLISH][WORD], audio_dine, AUDIO_FILES_DINE)
		# note that the dine audio files are named using the english word + "-dine"


def keyfunc_eng(r: Row):
	return r[ENGLISH][NORMALIZED]


def keyfunc_dine(r: Row):
	return r[DINE][NORMALIZED]


def get_audio(lang, word, filename, directory):
	if not filename:
		filename = normalize(word)
	audio_path = filename + "-" + lang + ".m4a"
	if audio_path in directory:
		return "/".join([AUDIO_PATH, lang, audio_path])
	return ""
	
def get_english_audio_path(row: Row):
	return get_audio(ENGLISH, row[ENGLISH][WORD], row[ENGLISH][AUDIO], AUDIO_FILES_ENG)

def get_dine_audio_path(row: Row):
	return get_audio(DINE, row[ENGLISH][WORD], row[DINE][AUDIO], AUDIO_FILES_DINE)
	# note that the dine audio files are named using the english word + "dine"


class Settable(ABC):
	def __init__(self, lang):
		self.lang = lang
		self.data = {}
	
	def set(self, row, key):
		value = row[self.lang][key]
		
		if not value:
			return
		
		try:
			ref_match = ref_pattern.match(value)
			if ref_match:
				# it's an @ reference
				word = row[ENGLISH][WORD]
				index = (word, ref_match.group(1))
				original_row = raw_rows[ENGLISH][index]
				# at the moment the references are always defined from the english side :/
				
				value = original_row[self.lang][key]
		except TypeError:
			# it's not a string, actually
			pass
		
		if value:
			self.data[key] = value
			
	def dump(self):
		return {k: v for (k, v) in self.data.items() if v and k != VARIANT}
	
	def __str__(self):
		return str(self.dump())
		


class SeeAlso:
	def __init__(self):
		self.entries = {}
	
	def add_row(self, row, lang):
		lang_row = row[lang]
		see_also = lang_row[SEE_ALSO]
		ref_match = ref_pattern.match(see_also)
		if ref_match:
			# it's an @ reference
			index = (lang_row[WORD], ref_match.group(1))
			see_also = raw_rows[ENGLISH][index][lang][SEE_ALSO]
			
		
		for word in see_also.split(", "):
			if word:
				self.entries[normalize(word)] = word
	
	def add(self, attr):
		return partial(self.add_row, attr)
	
	def update(self, *others: 'SeeAlso'):
		for other in others:
			self.entries.update(other.entries)
	
	
	def has_entries(self):
		return len(self.entries) > 0
	
	def dump(self):
		return [{"word": word, "normalized": normalized} for (normalized, word) in self.entries.items()]
	
	
class Dictionary:
	def __init__(self, lines):
		self.english = {}
		self.dine = {}
		
		unsorted_rows = [Row(line.strip("\n").split(CSV_DIVIDER)) for line in lines]
		
		# filter out rows missing a translation or definition
		filtered_rows = [row for row in unsorted_rows
		                 if row[ENGLISH][WORD]
		                 and row[DINE][WORD]
		                 and row[ENGLISH][DEFINITION]
		                 and row[DINE][DEFINITION]]
		
		# sort to ensure that we don't reference variants we haven't seen yet
		rows = sorted(filtered_rows, key=lambda r: normalize(r[ENGLISH][WORD]) + r[ENGLISH][VARIANT])
		
		# I think doing something like this and establishing a lookup would make things
		# much easier when trying to get variants
		raw_rows[ENGLISH] = {(row[ENGLISH][WORD], row[ENGLISH][VARIANT]): row
		                     for row in sorted(rows, key=keyfunc_eng)}
		raw_rows[DINE] = {(row[DINE][WORD], row[DINE][VARIANT]): row
		                    for row in sorted(rows, key=keyfunc_dine)}
		
		# TODO so we won't need to have these
		eng_rows = itertools.groupby(sorted(rows, key=keyfunc_eng), keyfunc_eng)
		dine_rows = itertools.groupby(sorted(rows, key=keyfunc_dine), keyfunc_dine)
		
		for (eng_key, word_rows) in eng_rows:
			# print(eng_key, *word_rows)
			if not eng_key:
				continue
				
			entry = DictionaryEntry(eng_key, ENGLISH)
			
			for row in word_rows:
				entry.add(row, DINE)
			self.english[eng_key] = entry
		
		for (dine_key, word_rows) in dine_rows:
			if not dine_key:
				continue
			
			entry = DictionaryEntry(dine_key, DINE)
			
			for row in word_rows:
				entry.add(row, ENGLISH)
			self.dine[dine_key] = entry
	
	def dump(self, out):
		english = {k: e.dump() for (k, e) in self.english.items()}
		dine = {k: e.dump() for (k, e) in self.dine.items()}
		json.dump({"entries": {ENGLISH: english, DINE: dine}},
		          out, indent=2, ensure_ascii=False)


class DictionaryEntry(Settable):
	keys_to_skip = [DEFINITION, SENTENCE]
	
	def __init__(self, word, lang):
		super().__init__(lang)
		self.word = word
		self.see_also = SeeAlso()
		self.short_translations = []
		self.translations = []
		self.definitions = {}
	
	def add(self, row, to_lang):
		for key in row[self.lang]:
			if key not in self.keys_to_skip:
				self.set(row, key)
		
		self.short_translations.append(row[to_lang][WORD])
		self.add_definition(row)
		self.add_translation(row, to_lang)
		self.see_also.add_row(row, self.lang)
	
	def add_definition(self, row):
		definition = row[self.lang][DEFINITION]
		word = row[ENGLISH][WORD]
		ref_match = ref_pattern.match(definition)
		
		if ref_match:
			ref = ref_match.group(1)
			row = raw_rows[ENGLISH][(word, ref)]
			definition = row[self.lang][DEFINITION]
		
		if definition and definition not in self.definitions:
			self.definitions[definition] = WordEntry(row, self.lang)
	
	def add_translation(self, row, to_lang):
		translation = Translation(row, to_lang)
		translation.see_also.add_row(row, to_lang)
		self.translations.append(translation)
	
	@staticmethod
	def translation_keyfunc(translation):
		try:
			return translation.data[DEFINITION]
		except KeyError:
			# for some reason there's no definition
			return ""
	
	def dump_translations(self):
		# FIXME this functionality should probably be extracted into its own class.
		# Possibly TranslationEntry, which is currently unused
		grouped = itertools.groupby(self.translations, key=self.translation_keyfunc)
		out = []
		
		for (definition, group) in grouped:
			see_also = SeeAlso()
			entries = []
			translation = {DEFINITION: definition}
			
			for entry in list(group):
				see_also.update(entry.see_also)
				entries.append(entry.dump())
				
				try:
					translation[SENTENCE] = entry.data[SENTENCE]
				except KeyError:
					# nbd, we just don't have a sentence for this entry
					pass
			
			if see_also.has_entries():
				translation[SEE_ALSO] = see_also.dump()
			if entries:
				translation["entries"] = entries
			
			out.append(translation)
		return out
	
	def dump(self):
		out = super().dump()
		if VARIANT in out:
			del out[VARIANT]  # we don't need to see this
		out["short_translations"] = self.short_translations
		if self.see_also.has_entries():
			out[SEE_ALSO] = self.see_also.dump()
		out["definitions"] = [e.dump() for e in self.definitions.values()]
		out["translations"] = self.dump_translations()
		return out
	

class Translation(Settable):
	keys_to_skip = []
	
	def __init__(self, row, lang):
		super().__init__(lang)
		self.see_also = SeeAlso()
		for key in row[lang]:
			if key not in self.keys_to_skip:
				self.set(row, key)
	
	def dump(self):
		out = super().dump()
		
		for key in [DEFINITION, SENTENCE, SEE_ALSO]:
			if key in out:
				del out[key]
		return out
	
	
class WordEntry(Settable):
	keys_to_skip = [WORD, NORMALIZED, SEE_ALSO, AUDIO, PHONETIC, COMMENT, LITERAL]
	
	def __init__(self, row, lang):
		super().__init__(lang)
		
		for key in row[lang]:
			if key not in self.keys_to_skip:
				self.set(row, key)

def main():
	with open("translation.tsv", encoding='utf-8') as csv:
		header_row, *rest = csv
		dictionary = Dictionary(rest)
	
	with open("translation.json", "w", encoding='utf-8') as out:
		dictionary.dump(out)


if __name__ == "__main__":
	main()
