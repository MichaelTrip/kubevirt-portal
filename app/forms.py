from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SelectField, FieldList, FormField, FieldList
from wtforms.validators import DataRequired, NumberRange

class ServicePortForm(FlaskForm):
    port_name = StringField('Port Name', validators=[DataRequired()])
    port = IntegerField('Port', validators=[DataRequired()])
    protocol = SelectField('Protocol', choices=[('TCP', 'TCP'), ('UDP', 'UDP')], default='TCP')
    targetPort = IntegerField('Target Port', validators=[DataRequired()])

    class Meta:
        # Disable CSRF for nested forms
        csrf = False

class TagForm(FlaskForm):
    key = StringField('Key', validators=[DataRequired()])
    value = StringField('Value', validators=[DataRequired()])
    
    class Meta:
        csrf = False

class VMForm(FlaskForm):
    vm_name = StringField('VM Name', validators=[DataRequired()])
    tags = FieldList(FormField(TagForm), min_entries=1)
    subdirectory = StringField('YAML Subdirectory', default='vms')
    cpu_cores = IntegerField('CPU Cores', validators=[DataRequired(), NumberRange(min=1, max=16)])
    memory = IntegerField('Memory (GB)', validators=[DataRequired(), NumberRange(min=1, max=64)])
    storage_size = IntegerField('Storage Size (GB)', validators=[DataRequired(), NumberRange(min=1, max=2048)])
    storage_class = StringField('Storage Class', default='longhorn-rwx')
    storage_access_mode = SelectField('Storage Access Mode', 
                                    choices=[('ReadWriteMany', 'ReadWriteMany'),
                                           ('ReadWriteOnce', 'ReadWriteOnce'),
                                           ('ReadOnlyMany', 'ReadOnlyMany')],
                                    default='ReadWriteMany')
    image_url = StringField('Image URL', validators=[DataRequired()])
    user_data = TextAreaField('User Data')
    hostname = StringField('Hostname')
    address_pool = StringField('Address Pool')
    service_type = SelectField('Service Type',
                             choices=[('LoadBalancer', 'LoadBalancer'),
                                    ('ClusterIP', 'ClusterIP')],
                             default='LoadBalancer')
    service_ports = FieldList(FormField(ServicePortForm), min_entries=1)
