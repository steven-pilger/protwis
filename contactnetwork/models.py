from structure.models import Structure

from django.db import models

class InteractingResiduePair(models.Model):
    referenced_structure = models.ForeignKey('structure.Structure', on_delete=models.CASCADE)
    res1 = models.ForeignKey('residue.Residue', related_name='residue1', on_delete=models.CASCADE)
    res2 = models.ForeignKey('residue.Residue', related_name='residue2', on_delete=models.CASCADE)


    @classmethod
    def truncate(cls):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('TRUNCATE TABLE "{0}" RESTART IDENTITY CASCADE'.format(cls._meta.db_table))

    class Meta():
        db_table = 'interacting_residue_pair'


class Interaction(models.Model):
    interacting_pair = models.ForeignKey('contactnetwork.InteractingResiduePair', on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=100)
    specific_type = models.CharField(max_length=100, null=True)

    # interaction_level -> 0 - normal definition, 1 - loosened definition
    interaction_level = models.IntegerField(null=False, default=0)
    atomname_residue1 = models.CharField(max_length=10, null=True)
    atomname_residue2 = models.CharField(max_length=10, null=True)

    @classmethod
    def truncate(cls):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('TRUNCATE TABLE "{0}" RESTART IDENTITY CASCADE'.format(cls._meta.db_table))

    class Meta():
        db_table = 'interaction'

class ConsensusInteraction(models.Model):
    gn1 = models.ForeignKey('residue.ResidueGenericNumber', on_delete=models.CASCADE, related_name='GN_1')
    gn2 = models.ForeignKey('residue.ResidueGenericNumber', on_delete=models.CASCADE, related_name='GN_2')
    protein_class = models.ForeignKey('protein.ProteinFamily', on_delete=models.CASCADE)
    state = models.ForeignKey('protein.ProteinState', on_delete=models.CASCADE)
    frequency = models.DecimalField(max_digits=5, decimal_places=2)
    structures = models.ManyToManyField('structure.Structure')
    proteins = models.ManyToManyField('protein.Protein')
    state_specific = models.BooleanField(default=False)

    class Meta():
        unique_together = ('gn1', 'gn2','protein_class','state')

class Distance(models.Model):
    structure = models.ForeignKey('structure.Structure', related_name='distances', on_delete=models.CASCADE, null=True)
    res1 = models.ForeignKey('residue.Residue', related_name='distance_residue1', on_delete=models.CASCADE, null=True)
    res2 = models.ForeignKey('residue.Residue', related_name='distance_residue2', on_delete=models.CASCADE, null=True)
    gn1 = models.CharField(max_length=100, null=True)
    gn2 = models.CharField(max_length=100, null=True)
    gns_pair = models.CharField(db_index=True, max_length=100, null=True)
    distance = models.IntegerField()

    @classmethod
    def truncate(cls):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('TRUNCATE TABLE "{0}" RESTART IDENTITY CASCADE'.format(cls._meta.db_table))

    class Meta():
        db_table = 'distance'
