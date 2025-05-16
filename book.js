// This will provide library work utilities in the future.

function saveAsStendhalFile() {
	let stendhalText =  `title: ${document.querySelector('[property="og:title"]').content}\n`
	                +   `author: ${document.querySelector('[class="signee-name"]').innerText}\n`
	                +   "pages:\n";
	Array.from(document.getElementsByClassName("page-content")).forEach(page => {
		stendhalText += `#- ${page.textContent}\n`;
	});
	stendhalText += "#- ";

	// output to file, download, and cleanup
	const element = document.createElement('a');
	element.href = window.URL.createObjectURL(new Blob([stendhalText]));
	// use page title as filename. Consider using `book title-author-iteration` instead  
	element.download = `${document.getElementsByTagName("title")[0].innerText}.stendhal`;
	element.style.display = 'none';
	document.body.appendChild(element);
	element.click();
	document.body.removeChild(element);
}

function insertStendhalDownloadButton() {
    var buttonNode = document.createElement('button');
    buttonNode.type = "button";
    buttonNode.onclick = () => saveAsStendhalFile();
    buttonNode.innerText = "Download as .Stendhal";

    var stendhalDownloadNode = document.createElement('div');
    stendhalDownloadNode.classList.add('download-button');
    stendhalDownloadNode.appendChild(buttonNode);

    let homeNode = document.getElementsByClassName("back-home")[0];
    homeNode.parentNode.insertBefore(stendhalDownloadNode, homeNode.nextSibling);
}

insertStendhalDownloadButton();