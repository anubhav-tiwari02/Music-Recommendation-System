// Demo dataset used by the UI prototype.
// This can be replaced with API responses from the model backend later.
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

// Normalize user input/title text so matching is more forgiving.
function normalize(value) {
  return value.trim().toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, ' ');
}

// Resolve a query to the best available title.
// 1) exact normalized match
// 2) fallback similarity heuristic
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

// Form submit handler: match input title and display recommendations.
document.getElementById('searchForm').addEventListener('submit', (event) => {
  event.preventDefault();
  const query = document.getElementById('songInput').value;
  const status = document.getElementById('status');
  const matchInfo = document.getElementById('matchInfo');

  status.textContent = '';
  status.classList.remove('error');
  matchInfo.style.display = 'none';

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
