if (!String.prototype.includes) {
  String.prototype.includes = function(search, start) {
    'use strict';
    if (typeof start !== 'number') {
      start = 0;
    }

    if (start + search.length > this.length) {
      return false;
    } else {
      return this.indexOf(search, start) !== -1;
    }
  };
}
if (!Array.prototype.includes) {
  Object.defineProperty(Array.prototype, "includes", {
    enumerable: false,
    value: function(obj) {
        var newArr = this.filter(function(el) {
          return el == obj;
        });
        return newArr.length > 0;
      }
  });
}

function displayError(message) {
  var pre = document.createElement('pre');
  pre.innerText = '' + message;
  document.body.appendChild(pre);
  pre.classList.add('error');
}

try {
  var indexJsonPromise = null;

  var matchQueryParams = location.search.match(/[?&]search=([^?&#]+)/);
  if (matchQueryParams) updateSearchResults(decodeURIComponent(matchQueryParams[1]));

  function getIndexJson() {
    if (!indexJsonPromise) {
      indexJsonPromise = new Promise(function (onData, onErr) {
        getUrl('books/index.json').then(JSON.parse).then(onData, onErr);
      });
    }
    return indexJsonPromise;
  }

  function updateSearchResults(query, maxResultsCount) {
    maxResultsCount = +maxResultsCount || 20;
    // get query from arg or text box, ensure it's a string
    query = '' + (query || document.getElementById('query').value);
    // set text box content to query
    document.getElementById('query').value = query;
    // reflect query in title
    document.title = 'Civ Book Viewer';
    if (query) document.title += ': ' + query;
    // set url to search for query
    if (!location.search.match(new RegExp('[?&]search=' + encodeURIComponent(query) + '($|&)'))) {
      var nextUrl = location.origin + location.pathname;
      if (query) nextUrl += "?search=" + encodeURIComponent(query);
      nextUrl += location.hash;
      // prevent page reload
      history.pushState(null, document.title, nextUrl);
    }
    var hintsNode = document.getElementById('search-hints');
    var loadAnimNode = document.getElementById('search-animation');
    var resultsNode = document.getElementById('search-results');
    if (!query) {
      hintsNode.classList.remove('hidden');
      loadAnimNode.classList.add('hidden');
      resultsNode.classList.add('hidden');
      removeAllChildNodes(resultsNode);
      return;
    }

    var indexJsonPromise = getIndexJson();
    loadAnimNode.classList.remove('hidden');
    hintsNode.classList.add('hidden');
    resultsNode.classList.add('hidden');
    removeAllChildNodes(resultsNode);

    var queryServers = [];
    var querySignees = [];
    var queryWords = [];

    ('' + query).split(' ').forEach(function (word) {
      word = word.toLowerCase();
      if (word.startsWith(':server:')) queryServers.push(word.replace(':server:', ''));
      else if (word.startsWith(':signee:')) querySignees.push(word.replace(':signee:', ''));
      else queryWords.push(word);
    });

    indexJsonPromise.then(function (indexJson) {
      var resultSlotsLeft = maxResultsCount;
      var hasMoreResults = false; // true if a maxResultsCount+1 'th book is found

      var results = Object.keys(indexJson).map(function (key) { return indexJson[key]; }).filter(filter)
      function filter(book) {
        // -1 to check one more book
        if (resultSlotsLeft <= -1) return false;
        if (querySignees.length > 0) {
          if (!querySignees.includes(book.signee.toLowerCase())) return false;
        }
        if (queryServers.length > 0) {
          var safeItemOrigin = book.item_origin.toLowerCase().replace(/ /g, '_').replace(/\.0$/, '');
          if (!queryServers.includes(safeItemOrigin)) return false;
        }
        var hasAllWords = true;
        queryWords.forEach(function (word) {
          if (!book.item_title.toLowerCase().includes(word)) hasAllWords = false;
        });
        if (!hasAllWords) return false;
        // it's a match!
        resultSlotsLeft -= 1;
        if (resultSlotsLeft <= -1) {
          hasMoreResults = true;
          return false; // don't show this book, it's above the result count limit
        }
        return true;
      }

      // replace progress animation with results
      loadAnimNode.classList.add('hidden');
      removeAllChildNodes(resultsNode);
      results.forEach(function (book) {
        resultsNode.appendChild(bookToNode(book));
      });
      if (hasMoreResults) {
        resultsNode.appendChild(document.createTextNode(
          'Displaying only the first ' + maxResultsCount + ' results.'));
      }
      if (results.length <= 0) {
        resultsNode.innerText = 'No books match that search. Try something else?';
        hintsNode.classList.remove('hidden');
      }
      resultsNode.classList.remove('hidden');
    }).catch(function (error) {
      loadAnimNode.classList.add('hidden');
      resultsNode.classList.remove('hidden');
      resultsNode.innerText = 'Error while searching: ' + error;
    });
  }

  function bookToNode(book) {
    var titleNode = document.createElement('a');
    var safeTitle = book.item_title.replace(/[ \\%:/?&#\'\"\[\]<>()]/g, '_');
    titleNode.setAttribute('href', 'books/' + book.signee + '/' + safeTitle + '.html');
    titleNode.classList.add('title');
    titleNode.innerText = book.item_title;

    var signeeNameNode = document.createElement('a');
    signeeNameNode.classList.add('signee-name');
    signeeNameNode.setAttribute('href', '?search=:signee:' + book.signee);
    signeeNameNode.innerText = book.signee;

    var signeeNode = document.createElement('div');
    signeeNode.classList.add('signee');
    signeeNode.appendChild(document.createTextNode('Signed by '));
    signeeNode.appendChild(signeeNameNode);

    var itemOriginNode = document.createElement('a');
    itemOriginNode.classList.add('server-name');
    var safeItemOrigin = book.item_origin.replace(/ /g, '_').replace(/\.0$/, '');
    itemOriginNode.setAttribute('href', '?search=:server:' + safeItemOrigin);
    itemOriginNode.innerText = book.item_origin;

    var serverNode = document.createElement('div');
    serverNode.classList.add('server');
    serverNode.appendChild(document.createTextNode('on '));
    serverNode.appendChild(itemOriginNode);

    var statsNode = document.createElement('div');
    statsNode.classList.add('stats');
    statsNode.appendChild(document.createTextNode(
      pluralize(book.word_count, 'word', 'words')
      + ' on ' + pluralize(book.page_count, 'page', 'pages')));

    var resultNode = document.createElement('div');
    resultNode.classList.add('search-result');
    resultNode.appendChild(titleNode);
    resultNode.appendChild(signeeNode);
    resultNode.appendChild(serverNode);
    resultNode.appendChild(statsNode);
    return resultNode;
  }

  function pluralize(num, singular, plural) {
    if (num == 1) return '' + num + ' ' + singular;
    return '' + num + ' ' + plural;
  }

  function removeAllChildNodes(node) {
    for (var i = node.childNodes.length - 1; i >= 0; i--) {
      node.childNodes[i].remove();
    }
  }

  function getUrl(url) {
    try {
      return new Promise(function (onData, onErr) {
        var request = new XMLHttpRequest();
        request.open('GET', url, true);
        request.onabort = function (e) { onErr('abort'); };
        request.onerror = function (e) { onErr('error'); };
        request.ontimeout = function (e) { onErr('timeout'); };
        request.onreadystatechange = function () {
          if (this.readyState === 4) {
            if (this.status >= 200 && this.status < 400) {
              onData(this.responseText);
            } else {
              onErr('status ' + this.status);
            }
          }
        }
        request.send();
        request = null;
      });
    } catch (e) {
      onErr(e);
    }
  }

} catch (e) {
  displayError('Error loading search: ' + e)
}
