// API endpoint for recommendation inference.
const API_BASE_URL = 'http://localhost:8001';

// Render recommendation cards into the results container.
const mockRecommendations = {
  Blindman: [
    { artist: 'The Handsome Family', song: 'Weightless Again' },
    { artist: 'Nick Drake', song: 'River Man' },
    { artist: 'Tom Waits', song: 'Hold On' },
    { artist: 'Leonard Cohen', song: 'Famous Blue Raincoat' },
    { artist: 'Bob Dylan', song: 'Shelter from the Storm' },
  ],
  Yellow: [
    { artist: 'Coldplay', song: 'Shiver' },
    { artist: 'Keane', song: 'Somewhere Only We Know' },
    { artist: 'Snow Patrol', song: 'Chasing Cars' },
    { artist: 'The Fray', song: 'How to Save a Life' },
    { artist: 'OneRepublic', song: 'Apologize' },
  ],
};

const titles = Object.keys(mockRecommendations);

function normalize(value) {
  return value.trim().toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, ' ');
}

function getClosestTitle(query) {
  const cleanQuery = normalize(query);
  const exact = titles.find((title) => normalize(title) === cleanQuery);
  if (exact) return { matched: exact, fuzzy: false };

  let best = null;
  let bestScore = -1;

  for (const title of titles) {
    const cleanTitle = normalize(title);

    // simple similarity score using token overlap + prefix hint
    const queryTokens = new Set(cleanQuery.split(' '));
    const titleTokens = new Set(cleanTitle.split(' '));

    const overlap = [...queryTokens].filter((t) => titleTokens.has(t)).length;
    const tokenScore = overlap / Math.max(queryTokens.size, titleTokens.size, 1);
    const prefixScore = cleanTitle.startsWith(cleanQuery) || cleanQuery.startsWith(cleanTitle) ? 0.2 : 0;
    const score = tokenScore + prefixScore;

    if (score > bestScore) {
      best = title;
      bestScore = score;
    }
  }

  if (bestScore < 0.35) return null;
  return { matched: best, fuzzy: true };
}

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
document.getElementById('searchForm').addEventListener('submit', (event) => {
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
    status.textContent = `Showing top recommendations for "${result.matched_song}"`;
  } catch (error) {
    document.getElementById('results').innerHTML = '';
    status.textContent = error.message || 'Could not fetch recommendations.';
    status.classList.add('error');
  } finally {
    setLoading(false);
  }
  const match = getClosestTitle(query);
  if (!match) {
    document.getElementById('results').innerHTML = '';
    status.textContent = 'No close match found. Try another song title.';
    status.classList.add('error');
    return;
  }

  if (match.fuzzy) {
    matchInfo.textContent = `Closest match: ${match.matched}`;
    matchInfo.style.display = 'inline-block';
  }

  renderResults(mockRecommendations[match.matched]);
  status.textContent = `Showing top recommendations for "${match.matched}"`;
});
