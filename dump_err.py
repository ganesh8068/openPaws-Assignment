import traceback
import sys

try:
    import models
    models.init_db()
except Exception as e:
    with open('err.txt', 'w') as f:
        traceback.print_exc(file=f)
