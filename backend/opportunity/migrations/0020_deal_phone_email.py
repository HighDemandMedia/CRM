from django.db import migrations, models
import common.validators

class Migration(migrations.Migration):
    dependencies = [('opportunity', '0019_opportunity_language')]
    operations = [
        migrations.AddField(model_name='opportunity',name='phone',field=models.CharField(max_length=25,blank=True,null=True,validators=[common.validators.flexible_phone_validator])),
        migrations.AddField(model_name='opportunity',name='email',field=models.EmailField(max_length=254,blank=True,null=True)),
    ]
