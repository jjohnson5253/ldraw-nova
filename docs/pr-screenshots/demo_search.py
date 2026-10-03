import json, sys
from ldraw_tools.resources import search_models
result = search_models('tugboat', root=sys.argv[1], database=sys.argv[2])
print(json.dumps({'query_language': result['query_language'], 'total': result['total'],
                  'files': [r['model'] for r in result['results']], 'truncated': result['truncated']}, indent=2))
