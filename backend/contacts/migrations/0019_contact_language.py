from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("contacts", "0018_contact_language")]
    operations = [migrations.AlterField(model_name="contact", name="language", field=models.CharField("Language", max_length=100, choices=[('English', 'English'), ('Spanish', 'Spanish'), ('French', 'French'), ('Portuguese', 'Portuguese'), ('Chinese', 'Chinese'), ('Arabic', 'Arabic'), ('Haitian Creole', 'Haitian Creole'), ('Russian', 'Russian'), ('German', 'German'), ('Italian', 'Italian'), ('Hindi', 'Hindi'), ('Other', 'Other')], blank=True, default=""))]
