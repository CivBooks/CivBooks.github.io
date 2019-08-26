if (!String.prototype.includes) {
  String.prototype.includes = function (search, start) {
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
    value: function (obj) {
      var newArr = this.filter(function (el) {
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
        getUrl('books/metadata.json').then(JSON.parse).then(onData, onErr);
      });
    }
    return indexJsonPromise;
  }

  function updateSearchResults(query, maxResultsCount) {
    maxResultsCount = +maxResultsCount || 20;
    // get query from arg or text box, ensure it's a string
    query = query || document.getElementById('query').value;
    query = ('' + query).trim();
    // set text box content to query
    document.getElementById('query').value = query;
    // reflect query in title
    if (query) document.title = 'Search: ' + query + ' - Civ Books';
    else document.title = 'Civ Books';
    // set url to search for query
    if (!location.search.match(new RegExp('[?&]search=' + encodeURIComponent(query) + '($|&)'))) {
      var nextUrl = location.origin + location.pathname;
      if (query) nextUrl += "?search=" + encodeURIComponent(query);
      nextUrl += location.hash;
      // prevent page reload
      history.pushState(null, document.title, nextUrl);
    }
    var searchStatusNode = document.getElementById('search-status');
    var resultsNode = document.getElementById('search-results');

    if (!query) {
      searchStatusNode.innerText = '';
      resultsNode.classList.add('hidden');
      removeAllChildNodes(resultsNode);
      return;
    }
    searchStatusNode.innerText = 'Searching ...';

    var indexJsonPromise = getIndexJson();
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
      var results = Object.keys(indexJson).map(function (key) { return indexJson[key]; }).filter(searchFilter);
      function searchFilter(book) {
        if (querySignees.length > 0) {
          if (!querySignees.includes(book.signee.toLowerCase())) return false;
        }

        // lazily computed
        var safeItemOrigin = null;
        function getSafeItemOrigin() {
          if (safeItemOrigin === null) safeItemOrigin = makeSafeOrigin(book.item_origin).toLowerCase();
          return safeItemOrigin;
        }

        if (queryServers.length > 0) {
          if (!queryServers.includes(getSafeItemOrigin())) return false;
        }

        var hasAllWords = true;
        queryWords.forEach(function (word) {
          if (
            !book.item_title.toLowerCase().includes(word)
            && !book.signee.toLowerCase().includes(word)
            && !book.item_origin.toLowerCase().includes(word)
            && !getSafeItemOrigin().toLowerCase().includes(word)
          ) {
            hasAllWords = false;
          }
        });
        if (!hasAllWords) return false;

        // it's a match!
        return true;
      }

      if (results.length <= 0) {
        searchStatusNode.innerText = 'No books match that search. Try something else?';
        return;
      } else {
        searchStatusNode.innerText = 'Found ' + results.length + ' matching books.';
      }

      results.sort(function (a, b) {
        var aTitle = (a.item_title || '').replace(re_format_code, '');
        var bTitle = (b.item_title || '').replace(re_format_code, '');
        return aTitle.localeCompare(bTitle);
      });
      removeAllChildNodes(resultsNode);
      results.slice(0, maxResultsCount).forEach(function (book) {
        resultsNode.appendChild(bookToNode(book));
      });
      resultsNode.classList.remove('hidden');
      // give the browser a chance to render the first results
      setTimeout(function () {
        var numRemaining = results.length - maxResultsCount;
        if (numRemaining <= 0) return;
        var detailsNode = document.createElement('details');
        var summaryNode = document.createElement('summary');
        summaryNode.innerText = 'Show remaining ' + numRemaining + ' results';
        detailsNode.appendChild(summaryNode);
        results.slice(maxResultsCount).forEach(function (book) {
          detailsNode.appendChild(bookToNode(book));
        });
        resultsNode.appendChild(detailsNode);
      }, 0);
    }).catch(function (error) {
      resultsNode.classList.remove('hidden');
      searchStatusNode.innerText = 'Error while searching: ' + error;
    });
  }

  var re_bad_url_chars = /[ \\%:/?&#\'\"\[\]<>()]/g;
  var re_format_code = /§[0-9a-fklmnor]/gi;

  function bookToNode(book) {
    var titleNode = document.createElement('a');
    var safeItemOrigin = makeSafeOrigin(book.item_origin);
    var safeItemTitle = book.item_title.replace(re_bad_url_chars, '_').replace(re_format_code, '');
    titleNode.setAttribute('href', 'books/'
      + safeItemOrigin + '/'
      + book.signee + '/'
      + safeItemTitle + '.html');
    titleNode.classList.add('title');
    titleNode.innerText = book.item_title.replace(re_format_code, '');

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

  function makeSafeOrigin(origin) {
    return origin.replace(/ /g, '_').replace(/\.0$/, '');
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
