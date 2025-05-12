package main

import (
	"database/sql"
	"embed" // For embedding the SQL file
	"fmt"
	"log"

	// "os" // No longer needed for direct file access
	// "path/filepath" // No longer needed for direct file access

	_ "modernc.org/sqlite" // SQLite driver
)

//go:embed data/embedded_data.sql
var embeddedFS embed.FS // Embed as a file system

var embeddedSQL string // We'll populate this from embeddedFS

// Video struct to hold video data from the database
type Video struct {
	VideoID      string
	URL          string
	Title        string
	ChannelTitle string
	ViewCount    int
	EmbedURL     string // To be constructed
}

var db *sql.DB

// var dbPath string // No longer needed as DB is in-memory

// initDB initializes an in-memory database and populates it from the embedded SQL file.
func initDB() error {
	log.Println("Initializing in-memory database...")

	// Read the SQL content from the embedded file system
	sqlBytes, err := embeddedFS.ReadFile("data/embedded_data.sql")
	if err != nil {
		return fmt.Errorf("failed to read embedded_data.sql from embedded FS: %w", err)
	}
	embeddedSQL = string(sqlBytes) // Populate our global string

	// Open an in-memory SQLite database.
	// WAL mode is generally good for SQLite, even in-memory, for concurrency.
	// Busy timeout helps if there are concurrent writes (less likely for in-memory setup).
	database, err := sql.Open("sqlite", ":memory:?_journal_mode=WAL&_busy_timeout=5000")
	if err != nil {
		return fmt.Errorf("failed to open in-memory database: %w", err)
	}
	db = database // Assign to global var

	// Execute the embedded SQL to create schema and populate data.
	if embeddedSQL == "" {
		// This check is now after attempting to read from embeddedFS
		return fmt.Errorf("embedded_data.sql is empty after reading from FS. Ensure it's correctly embedded and populated")
	}

	log.Println("Executing embedded SQL to populate database...")
	_, err = db.Exec(embeddedSQL)
	if err != nil {
		db.Close() // Close DB if exec fails
		return fmt.Errorf("failed to execute embedded SQL: %w", err)
	}

	// Ping the database to ensure the connection is live (optional for in-memory but good practice)
	err = db.Ping()
	if err != nil {
		db.Close() // Close the connection if ping fails
		return fmt.Errorf("failed to ping in-memory database: %w", err)
	}

	log.Println("In-memory database initialized and populated successfully.")
	return nil
}

// getRandomVideo fetches a single random video from the database.
func getRandomVideo() (Video, error) {
	var video Video

	if db == nil {
		return video, fmt.Errorf("database connection is not initialized")
	}

	query := `SELECT video_id, url, title, channel_title, view_count FROM videos ORDER BY RANDOM() LIMIT 1;`
	row := db.QueryRow(query)

	err := row.Scan(&video.VideoID, &video.URL, &video.Title, &video.ChannelTitle, &video.ViewCount)
	if err != nil {
		if err == sql.ErrNoRows {
			return video, fmt.Errorf("no videos found in the database")
		}
		return video, fmt.Errorf("error scanning video row: %w", err)
	}

	// Construct the embed URL with autoplay and JS API enabled
	video.EmbedURL = fmt.Sprintf("https://www.youtube.com/embed/%s?autoplay=1&enablejsapi=1", video.VideoID)

	return video, nil
}

// getVideoCount returns the total number of videos in the database.
func getVideoCount() (int, error) {
	if db == nil {
		return 0, fmt.Errorf("database connection is not initialized")
	}

	var count int
	query := `SELECT COUNT(*) FROM videos;`
	err := db.QueryRow(query).Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("failed to get video count: %w", err)
	}
	return count, nil
}
