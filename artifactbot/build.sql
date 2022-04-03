CREATE TABLE IF NOT EXISTS pinglist (
  Username TEXT PRIMARY KEY,
  Added INT
);

INSERT INTO pinglist(Username, Added) VALUES("testuser", 1) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS suggestions (
  Username TEXT PRIMARY KEY,
  Suggestion TEXT,
  Created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO suggestions(Username, Suggestion) VALUES("username123", "This is a suggestion") ON CONFLICT DO NOTHING;
