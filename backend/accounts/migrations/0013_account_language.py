from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("accounts", "0012_home_improvement_industry")]
    operations = [migrations.AddField(model_name="account", name="language", field=models.CharField("Language", max_length=100, choices=[('English', 'English'), ('Spanish', 'Spanish'), ('French', 'French'), ('Portuguese', 'Portuguese'), ('Chinese', 'Chinese'), ('Arabic', 'Arabic'), ('Haitian Creole', 'Haitian Creole'), ('Russian', 'Russian'), ('German', 'German'), ('Italian', 'Italian'), ('Hindi', 'Hindi'), ('Other', 'Other')], blank=True, default=""))]
