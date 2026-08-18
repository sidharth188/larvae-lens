from database.firestore_config import db

print("Testing Firestore connection...")
try:
    doc_ref = db.collection('larvae_reports').document('test_doc')
    doc_ref.set({"status": "test"})
    print("Write successful!")
    doc_ref.delete()
    print("Delete successful!")
except Exception as e:
    import traceback
    traceback.print_exc()
