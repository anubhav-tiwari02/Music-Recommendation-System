// API endpoint for recommendation inference.
const API_BASE_URL = 'http://localhost:8001';

// Render recommendation cards into the results container.
function renderResults(items) {
  const results = document.getElementById('results');
  results.innerHTML = '';

  items.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'card';
    card.innerHTML = `<h3>${item.song}</h3><p>${item.artist}</p>`;
    results.appendChild(card);
  });
}

function setLoading(isLoading) {
  const button = document.querySelector('#searchForm button');
  button.disabled = isLoading;
  button.textContent = isLoading ? 'Loading...' : 'Get Recommendations';
}

async function fetchRecommendations(query, topN = 5) {
  const url = new URL('/api/recommend', API_BASE_URL);
  url.searchParams.set('song', query);
  url.searchParams.set('top_n', String(topN));

  const response = await fetch(url);
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error || 'Failed to fetch recommendations');
  }

  return payload;
}

// Form submit handler: match input title and display recommendations.
document.getElementById('searchForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const query = document.getElementById('songInput').value;
  const status = document.getElementById('status');
  const matchInfo = document.getElementById('matchInfo');

  status.textContent = '';
  status.classList.remove('error');
  matchInfo.style.display = 'none';

  setLoading(true);

  try {
    const result = await fetchRecommendations(query, 5);

    if (result.fuzzy_match) {
      matchInfo.textContent = `Closest match: ${result.matched_song}`;
      matchInfo.style.display = 'inline-block';
    }

    renderResults(result.recommendations || []);
    const modeSuffix = result.retrieval_mode ? ` (${result.retrieval_mode} retrieval)` : '';
    status.textContent = `Showing top recommendations for "${result.matched_song}"${modeSuffix}`;
  } catch (error) {
    document.getElementById('results').innerHTML = '';
    status.textContent = error.message || 'Could not fetch recommendations.';
    status.classList.add('error');
  } finally {
    setLoading(false);
  }
});
