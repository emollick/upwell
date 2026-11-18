"""Couple a real captive primer stroke to the editable native liquid charge."""
import bpy

def install():
    cell=bpy.data.objects['prop_capillary_cell']
    cell['slosh_angle']=0.
    cell.id_properties_ui('slosh_angle').update(min=-.24,max=.24,description='Signed residual free-surface angle after a primer or a guide impulse, in radians')
    for name in ('capillary_liquid','capillary_gas'):
        ob=bpy.data.objects[name]
        curve=ob.driver_add('rotation_euler',0);driver=curve.driver;driver.type='SCRIPTED'
        while driver.variables:driver.variables.remove(driver.variables[0])
        for var_name,key in (('stroke','primer_stroke'),('wave','slosh_angle')):
            var=driver.variables.new();var.name=var_name;var.targets[0].id=cell;var.targets[0].data_path='["'+key+'"]'
        # Rotation about the cylinder's physical axis keeps every section
        # inside the wick and preserves the liquid and gas volumes exactly.
        driver.expression='wave+0.125*stroke'

if __name__=='__main__':
    install();bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
