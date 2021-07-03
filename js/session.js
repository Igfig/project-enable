const VISITED = "visited";

function session() {
	if (localStorage.getItem(VISITED)) {
		// this isn't the user's first visit, we don't need to do anything
		return
	}
	
	// otherwise, display the popup
	document.getElementById("about-popup").className="visible"
	
	// and record that we've visited
	localStorage.setItem(VISITED, "true")
}

window.addEventListener("load", session);