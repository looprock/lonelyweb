package main

import (
	"embed"             // For embedding templates
	"encoding/json"     // For JSON responses
	"html/template"
	"log"
	"net/http"
	"path/filepath" // Still used for static files
	"strings"       // For Viper environment variable handling

	"github.com/spf13/viper" // For configuration
)

//go:embed templates
var templatesFS embed.FS

var templates *template.Template

// Data for the main page template
type PageData struct {
	TotalVideos  int
	ErrorMessage string
	Video        *Video // For initial load if we decide to pass it directly
}

func main() {
	// Initialize database connection
	err := initDB()
	if err != nil {
		log.Fatalf("Failed to initialize in-memory database: %v. Check embedded SQL and embedding process.", err)
	}
	defer func() {
		if db != nil {
			db.Close()
		}
	}()

	// Load templates from embedded file system
	templates = template.Must(template.ParseFS(templatesFS, "templates/*.html"))
	log.Println("Templates loaded from embedded file system.")

	// Serve static files (htmx.min.js, css - though htmx.min.js is not used in this version)
	staticDir, err := filepath.Abs("static")
	if err != nil {
		log.Fatalf("Failed to get absolute path for static directory: %v", err)
	}
	fs := http.FileServer(http.Dir(staticDir))
	http.Handle("/static/", http.StripPrefix("/static/", fs))
	log.Printf("Serving static files from: %s", staticDir)

	// HTTP Handlers
	http.HandleFunc("/", indexHandler)
	http.HandleFunc("/next-video-json", nextVideoJSONHandler) // New endpoint for fetching next video data

	// Configure Viper
	viper.SetDefault("server.port", "8080") // Default port
	viper.SetEnvPrefix("LONELYWEB")          // Prefix for environment variables (e.g., LONELYWEB_SERVER_PORT)
	viper.AutomaticEnv()
	viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_")) // Replace . with _ in env var names

	// Optional: Configure Viper to read from a config file (e.g., config.yaml)
	// viper.SetConfigName("config") // Name of config file (without extension)
	// viper.SetConfigType("yaml")   // REQUIRED if the config file does not have the extension in the name
	// viper.AddConfigPath(".")      // Optionally look for config in the working directory
	// viper.AddConfigPath("$HOME/.lonelyweb") // call multiple times to add many search paths
	// if err := viper.ReadInConfig(); err != nil {
	// 	if _, ok := err.(viper.ConfigFileNotFoundError); ok {
	// 		// Config file not found; ignore error if desired
	// 		log.Println("No config file found, using defaults/env vars.")
	// 	} else {
	// 		// Config file was found but another error was produced
	// 		log.Printf("Error reading config file: %s", err)
	// 	}
	// }

	port := viper.GetString("server.port")

	log.Printf("Starting server on http://localhost:%s (configurable via LONELYWEB_SERVER_PORT env var or config file)", port)
	err = http.ListenAndServe(":"+port, nil)
	if err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

func indexHandler(w http.ResponseWriter, r *http.Request) {
	log.Println("indexHandler: Received request for /")
	data := PageData{}

	totalVideos, err := getVideoCount()
	if err != nil {
		log.Printf("Error getting total video count for index: %v", err)
		data.ErrorMessage = "Could not retrieve total video count."
		// We can still render the page, maybe with a 0 count or an error indication
	}
	data.TotalVideos = totalVideos

	video, err := getRandomVideo()
	if err != nil {
		log.Printf("Error getting random video for index: %v", err)
		// It's important to distinguish this error from the TotalVideos error
		if data.ErrorMessage != "" {
			data.ErrorMessage += " Additionally, failed to load a video."
		} else {
			data.ErrorMessage = err.Error()
		}
	} else {
		data.Video = &video
	}

	log.Printf("indexHandler: Attempting to render index.html with data: %+v", data)
	err = templates.ExecuteTemplate(w, "index.html", data)
	if err != nil {
		log.Printf("Error executing index template: %v", err)
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
	}
}

func nextVideoJSONHandler(w http.ResponseWriter, r *http.Request) {
	log.Println("nextVideoJSONHandler: Received request for /next-video-json")
	video, err := getRandomVideo()

	w.Header().Set("Content-Type", "application/json")

	if err != nil {
		log.Printf("Error getting random video for JSON response: %v", err)
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
		return
	}

	// We only need to send data relevant for the player update
	// The Video struct in database.go already has EmbedURL updated with autoplay&enablejsapi
	// but for JS player, only VideoID is strictly needed, other fields are for display.
	responseVideo := struct {
		VideoID      string `json:"videoId"`
		Title        string `json:"title"`
		ChannelTitle string `json:"channelTitle"`
		ViewCount    int    `json:"viewCount"`
		URL          string `json:"url"`         // Original URL for linking
		EmbedURL     string `json:"embedUrl"`    // Embed URL, though JS might construct its own
	}{
		VideoID:      video.VideoID,
		Title:        video.Title,
		ChannelTitle: video.ChannelTitle,
		ViewCount:    video.ViewCount,
		URL:          video.URL,
		EmbedURL:     video.EmbedURL, // JS might primarily use VideoID
	}

	err = json.NewEncoder(w).Encode(responseVideo)
	if err != nil {
		log.Printf("Error encoding video to JSON: %v", err)
		// Header already set, status might have been implicitly 200 OK already.
		// Avoid writing header again if already written.
		// http.Error might be too late here if some JSON has been written.
		return // Log the error, client will likely experience a broken response
	}
	log.Printf("nextVideoJSONHandler: Sent video data for ID: %s", video.VideoID)
}
