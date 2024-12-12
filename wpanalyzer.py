import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List, Set, Optional
import sys
from datetime import datetime

class WordPressXMLAnalyzer:
    def __init__(self, xml_path: str):
        """Initialize the analyzer with the path to WordPress XML export file."""
        self.xml_path = xml_path
        self.tree = None
        self.root = None
        self.namespaces = {
            'wp': 'http://wordpress.org/export/1.2/',
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
        }

    def load_xml(self) -> bool:
        """Load and parse the XML file."""
        try:
            self.tree = ET.parse(self.xml_path)
            self.root = self.tree.getroot()
            return True
        except Exception as e:
            print(f"Error loading XML file: {e}", file=sys.stderr)
            return False

    def get_custom_post_types(self) -> Dict[str, int]:
        """Get all custom post types and their counts."""
        post_types = defaultdict(int)
        for item in self.root.findall(".//item"):
            post_type = item.find("./wp:post_type", self.namespaces)
            if post_type is not None:
                post_types[post_type.text] += 1
        return dict(post_types)

    def get_custom_fields(self, post_type_filter: Optional[str] = None) -> Dict[str, Set[str]]:
        """
        Get all custom fields grouped by post type.
        
        Args:
            post_type_filter: If provided, only return fields for this post type
        """
        fields_by_post_type = defaultdict(set)
        for item in self.root.findall(".//item"):
            post_type = item.find("./wp:post_type", self.namespaces)
            if post_type is not None:
                if post_type_filter and post_type.text != post_type_filter:
                    continue
                meta_keys = item.findall("./wp:postmeta/wp:meta_key", self.namespaces)
                for meta_key in meta_keys:
                    if meta_key.text and not meta_key.text.startswith('_'):
                        fields_by_post_type[post_type.text].add(meta_key.text)
        return dict(fields_by_post_type)

    def get_posts(self, post_type: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Get posts of a specific type with optional limit.
        
        Args:
            post_type: The type of posts to retrieve
            limit: Maximum number of posts to return (None for all)
        """
        posts = []
        for item in self.root.findall(".//item"):
            if item.find("./wp:post_type", self.namespaces).text != post_type:
                continue
                
            # Get basic post data
            post_data = {
                'title': item.find('title').text if item.find('title') is not None else '',
                'post_name': item.find('./wp:post_name', self.namespaces).text if item.find('./wp:post_name', self.namespaces) is not None else '',
                'post_id': item.find('./wp:post_id', self.namespaces).text if item.find('./wp:post_id', self.namespaces) is not None else '',
                'status': item.find('./wp:status', self.namespaces).text if item.find('./wp:status', self.namespaces) is not None else '',
                'post_date': item.find('./wp:post_date', self.namespaces).text if item.find('./wp:post_date', self.namespaces) is not None else '',
            }
            
            # Get custom fields
            custom_fields = {}
            for meta in item.findall("./wp:postmeta", self.namespaces):
                meta_key = meta.find("wp:meta_key", self.namespaces)
                meta_value = meta.find("wp:meta_value", self.namespaces)
                if meta_key is not None and meta_value is not None and not meta_key.text.startswith('_'):
                    custom_fields[meta_key.text] = meta_value.text
            
            if custom_fields:
                post_data['custom_fields'] = custom_fields
            
            # Get taxonomies
            taxonomies = defaultdict(list)
            for category in item.findall("category"):
                domain = category.get('domain', '')
                if domain:
                    taxonomies[domain].append({
                        'nicename': category.get('nicename', ''),
                        'name': category.text
                    })
            
            if taxonomies:
                post_data['taxonomies'] = dict(taxonomies)
            
            posts.append(post_data)
            
            if limit and len(posts) >= limit:
                break
                
        return posts

    def get_taxonomies(self) -> Dict[str, Dict]:
        """Get all taxonomies, their terms, and usage counts by post type."""
        taxonomy_data = defaultdict(lambda: {
            'terms': set(),
            'usage_by_post_type': defaultdict(int)
        })
        
        # First, get all taxonomy definitions
        for item in self.root.findall(".//wp:category", self.namespaces):
            nicename = item.find("wp:category_nicename", self.namespaces)
            if nicename is not None:
                taxonomy_data['category']['terms'].add(nicename.text)

        for item in self.root.findall(".//wp:tag", self.namespaces):
            nicename = item.find("wp:tag_slug", self.namespaces)
            if nicename is not None:
                taxonomy_data['post_tag']['terms'].add(nicename.text)

        # Then analyze term usage in posts
        for item in self.root.findall(".//item"):
            post_type = item.find("./wp:post_type", self.namespaces).text
            
            # Get categories
            categories = item.findall("category")
            for cat in categories:
                domain = cat.get('domain', '')
                if domain:  # This could be 'category', 'post_tag', or custom taxonomy
                    taxonomy_data[domain]['terms'].add(cat.get('nicename', ''))
                    taxonomy_data[domain]['usage_by_post_type'][post_type] += 1

        # Convert sets to sorted lists for better display
        result = {}
        for tax_name, data in taxonomy_data.items():
            result[tax_name] = {
                'terms': sorted(data['terms']),
                'usage_by_post_type': dict(data['usage_by_post_type']),
                'total_terms': len(data['terms'])
            }
        
        return result

def main():
    parser = argparse.ArgumentParser(
        description='Analyze WordPress XML export files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Examples:
    # Show all custom fields
    python wpanalyzer.py export.xml --custom-fields

    # Show custom fields for a specific post type
    python wpanalyzer.py export.xml --custom-fields --post-type=page

    # Show posts with their custom fields
    python wpanalyzer.py export.xml --show-posts=page

    # Show limited number of posts
    python wpanalyzer.py export.xml --show-posts=page --limit=5

    # Show all available post types
    python wpanalyzer.py export.xml --post-types

    # Show taxonomy information
    python wpanalyzer.py export.xml --taxonomies
        """
    )
    parser.add_argument('xml_file', help='Path to WordPress XML export file')
    parser.add_argument('--post-types', action='store_true', help='List all custom post types')
    parser.add_argument('--custom-fields', action='store_true', help='List all custom fields by post type')
    parser.add_argument('--post-type', help='Filter custom fields by post type')
    parser.add_argument('--taxonomies', action='store_true', help='List all taxonomies and their terms')
    parser.add_argument('--show-posts', help='Show posts of specific type')
    parser.add_argument('--limit', type=int, help='Limit number of posts shown')
    
    args = parser.parse_args()
    
    analyzer = WordPressXMLAnalyzer(args.xml_file)
    if not analyzer.load_xml():
        sys.exit(1)

    if args.post_types:
        post_types = analyzer.get_custom_post_types()
        print("\nPost Types Found:")
        print("-----------------")
        for post_type, count in post_types.items():
            print(f"{post_type}: {count} items")

    if args.custom_fields:
        custom_fields = analyzer.get_custom_fields(args.post_type)
        print("\nCustom Fields by Post Type:")
        print("-------------------------")
        if not custom_fields:
            if args.post_type:
                print(f"No custom fields found for post type: {args.post_type}")
            else:
                print("No custom fields found")
        else:
            for post_type, fields in custom_fields.items():
                print(f"\n{post_type}:")
                for field in sorted(fields):
                    print(f"  - {field}")

    if args.taxonomies:
        taxonomies = analyzer.get_taxonomies()
        print("\nTaxonomies Analysis:")
        print("-------------------")
        for tax_name, data in taxonomies.items():
            print(f"\n{tax_name}:")
            print(f"  Total Terms: {data['total_terms']}")
            print("  Usage by Post Type:")
            for post_type, count in data['usage_by_post_type'].items():
                print(f"    - {post_type}: {count} uses")
            print("  Terms:")
            # TODO: Later add some sort of filter arg that we can use here.
            for term in data['terms']:
                print(f"    - {term}")

    if args.show_posts:
        posts = analyzer.get_posts(args.show_posts, args.limit)
        if not posts:
            print(f"\nNo posts found of type: {args.show_posts}")
        else:
            print(f"\nPosts of type '{args.show_posts}':")
            print("-" * (len(args.show_posts) + 18))
            for post in posts:
                print(f"\nTitle: {post['title']}")
                print(f"ID: {post['post_id']}")
                print(f"Slug: {post['post_name']}")
                print(f"Status: {post['status']}")
                print(f"Date: {post['post_date']}")
                
                if 'custom_fields' in post:
                    print("Custom Fields:")
                    for field, value in post['custom_fields'].items():
                        if value is not None:
                            # TODO: previously had {value[:100]}{'...' if len(value) > 100 else ''} 
                            # in the future add a flag to control this.
                            print(f"  - {field}: {value}")
                        else:
                            # Here because if value is None it's not subscriptable
                            print(f"  - {field}: ''")
                
                if 'taxonomies' in post:
                    print("Taxonomies:")
                    for tax, terms in post['taxonomies'].items():
                        print(f"  {tax}:")
                        for term in terms:
                            print(f"    - {term['name']} ({term['nicename']})")
                print("-" * 40)

    if not (args.post_types or args.custom_fields or args.taxonomies or args.show_posts):
        parser.print_help()

if __name__ == "__main__":
    main()
