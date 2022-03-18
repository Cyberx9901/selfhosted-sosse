from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('se', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='''
              CREATE FUNCTION weight_vector() RETURNS trigger AS $$
              BEGIN
                new.vector = setweight(to_tsvector(new.vector_lang, new.normalized_title), 'A') ||
                             setweight(to_tsvector(new.vector_lang, new.normalized_url), 'A') ||
                             setweight(to_tsvector(new.vector_lang, (SELECT STRING_AGG(text, ' ') FROM se_link WHERE doc_to_id=new.id)), 'B') ||
                             setweight(to_tsvector(new.vector_lang, new.normalized_content), 'C');
                return new;
              END
              $$ LANGUAGE plpgsql;

              CREATE TRIGGER vector_column_trigger
              BEFORE INSERT OR UPDATE OF normalized_title, normalized_content, normalized_url, vector_lang
              ON se_document
              FOR EACH ROW EXECUTE PROCEDURE weight_vector();
            ''',

            reverse_sql = '''
              DROP TRIGGER IF EXISTS vector
              ON se_document;
            '''
        ),
    ]
