function search() {
	const params = new URLSearchParams(location.search);
	const search = params.get("search");
	
	if (!search) {
		return
	}
	
	const searchNormalized = search.replace("'", "").toLowerCase();
	// question: are there any other non-alphanumeric symbols we need to deal with besides apostrophes?
	let index = searchTerms.findIndex(tn => tn.startsWith(searchNormalized));
	const searchFound = index > -1;
	
	if (!searchFound) {
		// couldn't find the search term, so figure out the closest spot
		const withSearch = [...searchTerms, searchNormalized];
		withSearch.sort();
		index = withSearch.indexOf(search)
	}
	
	window.addEventListener("load", () => {
		document.getElementById(`d${index}`).focus();
		
		if (searchFound) {
			document.getElementById(`s${index}`).checked = true
		}
	});
}

search();