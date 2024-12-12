# wpanalyzer
Simple python cli to analyze xml files from wordpress exports. Used to get a closer look at
custom post types, custom fields, and taxonomies along with their content to get a better understanding of
the previous configuration.

## Usage
```bash
# Show all post types, custom fields and taxonomies
$ python wp_analyzer.py export.xml --post-types --custom-fields --taxonomies

# Show all posts w/ content
$ python wp_analyzer.py export.xml --show-posts=post

# Show specified number of posts w/ content
$ python wp_analyzer.py export.xml --show-posts=post --limit=2

# Show custom fields for specific post type
$ python wp_analyzer.py export.xml --custom-fields --post-type=post

```

### TODOs 
- [ ] Add export to json for ACF Pro imports
- [ ] Add export to CPT UI plugin format
- [ ] Expand on analysis functionality
