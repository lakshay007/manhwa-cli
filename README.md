# Manhwa CLI

A command-line tool to browse and read manhwas from [Toonily.com](https://toonily.com) directly from your terminal.

## Features

- Search for manhwas by name
- Browse search results with details (title, rating, latest chapter)
- View all available chapters for a selected manhwa
- Local image viewer for reading chapters offline without a browser
- User-friendly interface with colored output and interactive menus

## Installation

### Prerequisites

- Python 3.6 or higher
- pip (Python package manager)

### Install from Source

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/manhwa-cli.git
   cd manhwa-cli
   ```

2. Install the package:
   ```
   pip install -e .
   ```

## Usage

### Basic Usage

```bash
# Search for a manhwa
manhwa-cli solo leveling

# Limit the number of search results
manhwa-cli solo leveling --limit 5
```

### Interactive Features

1. After searching, you'll see a numbered list of results with details
2. Enter the number of the manhwa you want to read
3. You'll see a list of available chapters(Press N to move to the next page of the menu)
4. Enter the chapter number you want to read
5. The chapter will download and open as a PDF in your system's default PDF viewer
   - Take advantage of your PDF viewer's native features
   - The PDF is automatically cleaned up when you close the viewer


## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 