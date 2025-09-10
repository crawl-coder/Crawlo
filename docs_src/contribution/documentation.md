# Documentation Contribution Guide

This guide explains how to contribute to the Crawlo documentation, including writing style guidelines, structure, and processes.

## Documentation Structure

Crawlo documentation follows a hierarchical structure organized by topics and user needs:

```
docs/
├── getting_started/          # Quick start and installation guides
├── core_concepts/            # Fundamental concepts and architecture
├── development_guide/        # Detailed development guides
├── advanced_topics/          # Advanced features and techniques
├── configuration_reference/  # Detailed configuration options
├── api_reference/            # Complete API documentation
├── examples/                 # Real-world examples
├── troubleshooting/          # Common issues and solutions
└── contribution/             # Contribution guidelines
```

## Writing Style Guidelines

### Language and Tone

- Use clear, concise, and professional language
- Write in the second person ("you" rather than "the user")
- Maintain a helpful and approachable tone
- Avoid jargon unless it's commonly understood in the domain
- Define technical terms when first introduced

### Grammar and Mechanics

- Use American English spelling and grammar
- Write in active voice when possible
- Use present tense for general instructions
- Use past tense for describing results or outcomes
- Keep sentences and paragraphs short and focused

### Code Examples

- Provide complete, working code examples
- Include comments to explain complex parts
- Use consistent variable and function names
- Show both successful and error cases when relevant
- Format code according to the project's style guidelines

```python
# Good example with explanation
def parse(self, response):
    """Parse response and extract data."""
    # Extract title using CSS selector
    title = response.css('title::text').get()
    
    # Extract all links
    links = response.css('a::attr(href)').getall()
    
    yield {
        'title': title,
        'links': links
    }
```

## Documentation Types

### Tutorials

Tutorials are learning-oriented and guide users through complete tasks:

```markdown
# Creating Your First Spider

This tutorial will walk you through creating your first Crawlo spider.

## Prerequisites

- Python 3.10 or higher
- Basic knowledge of Python

## Step 1: Create a Project

First, create a new Crawlo project:

```bash
crawlo startproject my_first_project
cd my_first_project
```

## Step 2: Generate a Spider

Generate a spider template:

```bash
crawlo genspider example example.com
```

This creates `spiders/example.py` with basic spider structure.
```

### How-to Guides

How-to guides are goal-oriented and solve specific problems:

```markdown
# How to Handle Pagination

This guide explains how to handle pagination in your Crawlo spiders.

## Following Next Page Links

To follow pagination links, yield new requests in your parse method:

```python
def parse(self, response):
    # Extract data from current page
    for item in response.css('.item'):
        yield {'title': item.css('.title::text').get()}
    
    # Follow next page link
    next_page = response.css('.next-page::attr(href)').get()
    if next_page:
        yield response.follow(next_page, self.parse)
```
```

### Technical Reference

Technical reference is information-oriented and provides detailed specifications:

```markdown
# Request Class

## Class: Request

Represents an HTTP request to be downloaded.

### Parameters

- `url` (str): The URL of the request.
- `callback` (callable, optional): The function that will be called with the response.
- `method` (str, optional): The HTTP method. Defaults to 'GET'.
- `headers` (dict, optional): The HTTP headers for the request.
- `body` (bytes, optional): The request body.
- `cookies` (dict, optional): The cookies to send with the request.
- `meta` (dict, optional): Metadata for the request that will be accessible in the response.
```

### Explanation

Explanations are understanding-oriented and provide background knowledge:

```markdown
# Understanding the Crawlo Architecture

Crawlo follows a modular architecture where different components handle specific responsibilities:

## Engine

The Engine is the central coordinator that manages the crawling process. It orchestrates the interaction between the Scheduler, Downloader, and Processor components.

## Scheduler

The Scheduler manages the request queue and handles request deduplication. It ensures that the same request is not processed multiple times and manages the order in which requests are processed.

## Downloader

The Downloader is responsible for making HTTP requests and retrieving responses from web servers. Crawlo supports multiple downloader implementations including aiohttp, httpx, and curl-cffi.
```

## Documentation Formatting

### Headers

Use descriptive headers that clearly indicate the content:

```markdown
# Main Topic (H1)
## Section (H2)
### Subsection (H3)
#### Sub-subsection (H4)
```

### Lists

Use bulleted lists for unordered items and numbered lists for ordered steps:

```markdown
## Features

- Multiple execution modes
- Command-line interface
- Automatic spider discovery

## Installation Steps

1. Clone the repository
2. Install dependencies
3. Verify installation
```

### Code Blocks

Always specify the language for syntax highlighting:

```markdown
```python
def my_function():
    return "Hello, World!"
```

```bash
pip install crawlo
```

```javascript
console.log("Example");
```
```

### Links

Use descriptive link text rather than URLs:

```markdown
For more information, see the [Configuration Guide](configuration.md).

Visit the [GitHub repository](https://github.com/crawl-coder/Crawlo).
```

### Images

When including diagrams or screenshots:

```markdown
![Crawlo Architecture Diagram](../images/architecture.png)

*Figure 1: Crawlo architecture overview*
```

## API Documentation

### Docstrings

Use Google-style docstrings for API documentation:

```python
class Spider:
    """A web crawler that extracts data from websites.
    
    Spiders define how to crawl and parse a particular website or set of websites.
    They are the main entry point for crawling logic.
    
    Attributes:
        name: A unique identifier for the spider.
        start_urls: URLs where the spider will begin crawling.
    """
    
    def parse(self, response):
        """Parse a response and extract data or new requests.
        
        This method is called for each response that the spider downloads.
        It should parse the response data and return extracted items or new requests.
        
        Args:
            response: The Response object to parse.
            
        Yields:
            Item objects or Request objects.
            
        Example:
            >>> def parse(self, response):
            ...     for quote in response.css('div.quote'):
            ...         yield {
            ...             'text': quote.css('span.text::text').get(),
            ...             'author': quote.css('small.author::text').get(),
            ...         }
        """
        pass
```

### Cross-references

Link to related documentation:

```markdown
See [Request](../api_reference/network.md#request-class) for details on request objects.

For configuration options, refer to the [Settings Documentation](../configuration_reference/settings.md).
```

## Contributing Process

### 1. Fork and Clone

Fork the Crawlo repository and clone your fork:

```bash
git clone https://github.com/your-username/Crawlo.git
cd Crawlo
```

### 2. Create a Branch

Create a new branch for your documentation changes:

```bash
git checkout -b docs/your-documentation-topic
```

### 3. Write Documentation

Follow the guidelines in this document when writing documentation.

### 4. Preview Changes

Preview your documentation locally:

```bash
# Install documentation dependencies
pip install mkdocs-material

# Serve documentation locally
mkdocs serve
```

### 5. Validate Links

Check for broken links:

```bash
# Install link checker
pip install mkdocs-htmlproofer-plugin

# Build and check links
mkdocs build --strict
```

### 6. Commit Changes

Commit your changes with a clear, descriptive message:

```bash
git add docs/your-changed-files.md
git commit -m "docs: Add guide for handling pagination"
```

### 7. Submit Pull Request

Push your changes and create a pull request:

```bash
git push origin docs/your-documentation-topic
```

## Review Process

### Documentation Review Checklist

Before submitting documentation changes, review:

- [ ] Content is accurate and up-to-date
- [ ] Writing follows style guidelines
- [ ] Code examples are correct and complete
- [ ] Links are working and relevant
- [ ] Documentation is organized logically
- [ ] No spelling or grammar errors
- [ ] Consistent terminology usage

### Technical Accuracy

Ensure technical content is accurate:

- Verify code examples work as described
- Check that API references match implementation
- Confirm configuration examples are valid
- Test any commands or procedures documented

### User Experience

Consider the user experience:

- Is the documentation easy to navigate?
- Are concepts explained clearly?
- Do examples help understanding?
- Is the information findable?

## Versioning and Localization

### Version Management

Documentation should be versioned with the code:

- Major changes get new documentation versions
- Breaking changes are clearly marked
- Deprecated features are noted with migration paths

### Internationalization

Support for multiple languages:

- English is the primary language
- Other languages are maintained in separate files
- Use consistent terminology across translations
- Keep translations synchronized with source content

## Tools and Resources

### Documentation Tools

- **MkDocs**: Static site generator for project documentation
- **Material for MkDocs**: Theme and plugins for MkDocs
- **Markdown**: Documentation format
- **Grammarly**: Grammar and spelling checker

### Markdown Extensions

Crawlo documentation uses several Markdown extensions:

```markdown
=== "Python"
    ```python
    def example():
        pass
    ```

=== "JavaScript"
    ```javascript
    function example() {
        // JavaScript code
    }
    ```

--8<-- "includes/important-note.md"
```

## Common Documentation Tasks

### Adding New Pages

1. Create the Markdown file in the appropriate directory
2. Add the page to the navigation in `mkdocs.yml`
3. Include appropriate front matter if needed
4. Write content following the guidelines
5. Add cross-references to related pages

### Updating Existing Documentation

1. Identify what needs to be updated
2. Make minimal, focused changes
3. Verify that updates are technically accurate
4. Check that changes don't break existing links
5. Update any related documentation sections

### Adding Code Examples

1. Ensure examples are complete and runnable
2. Include necessary imports and setup
3. Add comments to explain complex parts
4. Test examples to verify they work
5. Format code according to style guidelines

### Creating Diagrams

1. Use clear, simple diagrams
2. Maintain consistent visual style
3. Include alt text for accessibility
4. Store images in the `docs/images/` directory
5. Reference images with relative paths

## Quality Assurance

### Peer Review

All documentation changes should be reviewed by:

- At least one other contributor
- Someone familiar with the technical content
- Someone who can review writing quality

### Automated Checks

Documentation should pass automated checks for:

- Spelling and grammar
- Link validation
- Markdown formatting
- Accessibility standards

### User Feedback

Monitor user feedback through:

- GitHub issues
- Documentation comments
- User surveys
- Support requests

By following these guidelines, you'll help maintain high-quality documentation that effectively supports Crawlo users and contributors.