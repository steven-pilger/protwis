from django.shortcuts import render
from django.db.models import Q, F, Prefetch
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.db import connection

from collections import defaultdict
from django.conf import settings

import json
import functools
import hashlib
import copy

from contactnetwork.models import *
from contactnetwork.distances import *
from structure.models import Structure, StructureVectors
from structure.templatetags.structure_extras import *
from construct.models import Construct
from protein.models import Protein, ProteinSegment
from residue.models import Residue, ResidueGenericNumber
from interaction.models import StructureLigandInteraction

Alignment = getattr(__import__('common.alignment_' + settings.SITE_NAME, fromlist=['Alignment']), 'Alignment')

from django.http import JsonResponse, HttpResponse
from collections import OrderedDict

import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
import scipy.spatial.distance as ssd
import time

def Clustering(request):
    """
    Show clustering page
    """
    return render(request, 'contactnetwork/clustering.html')

def Interactions(request):
    """
    Show interaction heatmap
    """

    template_data = {}
    # check for preselections in POST data
    if request.POST and (request.POST.get("pdbs1") != None or request.POST.get("pdbs2") != None):
        # handle post
        pdbs1 = request.POST.get("pdbs1")
        pdbs2 = request.POST.get("pdbs2")
        if pdbs1 == "":
            pdbs1 = None
        if pdbs2 == "":
            pdbs2 = None

        # create switch
        if pdbs1 != None and pdbs2 != None:
            template_data["pdbs1"] = '["' + '", "'.join(pdbs1.split("\r\n")) + '"]'
            template_data["pdbs2"] = '["' + '", "'.join(pdbs2.split("\r\n")) + '"]'
        else:
            if pdbs1 == None:
                template_data["pdbs"] = '["' + '", "'.join(pdbs2.split("\r\n")) + '"]'
            else:
                template_data["pdbs"] = '["' + '", "'.join(pdbs1.split("\r\n")) + '"]'

    return render(request, 'contactnetwork/interactions.html', template_data)

def InteractionBrowser(request):
    """
    Show interaction heatmap
    """

    template_data = {}
    # check for preselections in POST data
    if request.POST and (request.POST.get("pdbs1") != None or request.POST.get("pdbs2") != None):
        # handle post
        pdbs1 = request.POST.get("pdbs1")
        pdbs2 = request.POST.get("pdbs2")
        if pdbs1 == "":
            pdbs1 = None
        if pdbs2 == "":
            pdbs2 = None

        # create switch
        if pdbs1 != None and pdbs2 != None:
            template_data["pdbs1"] = '["' + '", "'.join(pdbs1.split("\r\n")) + '"]'
            template_data["pdbs2"] = '["' + '", "'.join(pdbs2.split("\r\n")) + '"]'
        else:
            if pdbs1 == None:
                template_data["pdbs"] = '["' + '", "'.join(pdbs2.split("\r\n")) + '"]'
            else:
                template_data["pdbs"] = '["' + '", "'.join(pdbs1.split("\r\n")) + '"]'

    return render(request, 'contactnetwork/browser.html', template_data)

def ShowDistances(request):
    """
    Show distances heatmap
    """

    template_data = {}

    if request.POST and (request.POST.get("pdbs1") != None or request.POST.get("pdbs2") != None):
        # check for preselections in POST data
        pdbs1 = request.POST.get("pdbs1")
        pdbs2 = request.POST.get("pdbs2")
        if pdbs1 == "":
            pdbs1 = None
        if pdbs2 == "":
            pdbs2 = None

        # create switch
        if pdbs1 != None and pdbs2 != None:
            template_data["pdbs1"] = '["' + '", "'.join(pdbs1.split("\r\n")) + '"]'
            template_data["pdbs2"] = '["' + '", "'.join(pdbs2.split("\r\n")) + '"]'
        else:
            if pdbs1 == None:
                template_data["pdbs"] = '["' + '", "'.join(pdbs2.split("\r\n")) + '"]'
            else:
                template_data["pdbs"] = '["' + '", "'.join(pdbs1.split("\r\n")) + '"]'

    return render(request, 'contactnetwork/distances.html', template_data)

def PdbTreeData(request):
    data = Structure.objects.values(
        'representative',
        'pdb_code__index',
        'protein_conformation__protein__parent__family__parent__parent__parent__name',
        'protein_conformation__protein__parent__family__parent__parent__name',
        'protein_conformation__protein__parent__family__parent__name',
        'protein_conformation__protein__parent__family__name',
        'protein_conformation__protein__parent__family__parent__parent__parent__slug',
        'protein_conformation__protein__parent__family__parent__parent__slug',
        'protein_conformation__protein__parent__family__parent__slug',
        'protein_conformation__protein__parent__family__slug',
        'protein_conformation__state__slug'
        ).exclude(refined=True)

    # TODO: Use ordereddict
    l = lambda:defaultdict(l)
    data_dict = l()

    for d in data:
        pdb = d['pdb_code__index']
        rep = d['representative']
        l3 = d['protein_conformation__protein__parent__family__name']
        l2 = d['protein_conformation__protein__parent__family__parent__name']
        l1 = d['protein_conformation__protein__parent__family__parent__parent__name']
        l0 = d['protein_conformation__protein__parent__family__parent__parent__parent__name']
        s3 = d['protein_conformation__protein__parent__family__slug']
        s2 = d['protein_conformation__protein__parent__family__parent__slug']
        s1 = d['protein_conformation__protein__parent__family__parent__parent__slug']
        s0 = d['protein_conformation__protein__parent__family__parent__parent__parent__slug']
        state = d['protein_conformation__state__slug']

        if rep:
            rep = 'R'
        else:
            rep = 'N'

        if state == 'active':
            state = 'A'
        else:
            state = 'I'

        if not data_dict[s0 + ',' + l0][s1 + ',' + l1][s2 + ',' + l2][s3 + ',' + l3]:
            data_dict[s0 + ',' + l0][s1 + ',' + l1][s2 + ',' + l2][s3 + ',' + l3] = []

        data_dict[s0 + ',' + l0][s1 + ',' + l1][s2 + ',' + l2][s3 + ',' + l3].append(pdb + ' (' + state + ')'  + '(' + rep + ')')

    return JsonResponse(data_dict)

# @cache_page(60*60*24*7)
def PdbTableData(request):

    constructs = Construct.objects.defer('schematics','snakecache').all().prefetch_related('crystallization__crystal_method')
    methods = {}
    for c in constructs:
        # print(c.name)
        if c.crystallization and c.crystallization.crystal_method:
            method = c.crystallization.crystal_method.name
        else:
            method = "N/A"
        methods[c.name] = method

    data = Structure.objects.filter(refined=False).prefetch_related(
                "pdb_code",
                "state",
                "stabilizing_agents",
                "structureligandinteraction_set__ligand__properities__ligand_type",
                "structureligandinteraction_set__ligand_role",
                "protein_conformation__protein__parent__parent__parent",
                "protein_conformation__protein__parent__family__parent",
                "protein_conformation__protein__parent__family__parent__parent__parent",
                "protein_conformation__protein__species",Prefetch("ligands", queryset=StructureLigandInteraction.objects.filter(
                annotated=True).prefetch_related('ligand__properities__ligand_type', 'ligand_role')))

    data_dict = OrderedDict()
    data_table = "<table id2='structure_selection' class='structure_selection row-border text-center compact text-nowrap' width='100%'><thead><tr><th colspan=5>Receptor</th><th colspan=8>Structure</th><th colspan=2>Signalling protein</th> \
                                                                       <th colspan=2>Auxiliary protein</th><th colspan=3>Ligand</th><th rowspan=2><input class='form-check-input check_all' type='checkbox' value='' onclick='check_all(this);'></th></tr> \
                  <tr><th></th><th></th><th></th><th></th><th></th><th></th><th></th><th></th><th></th><th>% of class active<br> state-specific contacts</th><th>% of class inactive<br> state-specific contacts</th><th></th><th></th><th></th><th></th><th></th><th></th><th></th><th></th><th></th></thead><tbody>\n"

    for s in data:
        pdb_id = s.pdb_code.index
        r = {}
        r['protein'] = s.protein_conformation.protein.parent.entry_short()
        r['protein_long'] = s.protein_conformation.protein.parent.short()
        r['protein_family'] = s.protein_conformation.protein.parent.family.parent.short()
        r['class'] = s.protein_conformation.protein.parent.family.parent.parent.parent.shorter()
        r['species'] = s.protein_conformation.protein.species.common_name
        # # r['date'] = s.publication_date
        r['state'] = s.state.name
        r['contact_representative'] = 'Yes' if s.contact_representative else 'No'
        r['contact_representative_score'] = "{:.0%}".format(s.contact_representative_score)

        r['active_class_contacts_fraction'] = "{:.0%}".format(s.active_class_contacts_fraction)
        r['inactive_class_contacts_fraction'] = "{:.0%}".format(s.inactive_class_contacts_fraction)

        a_list = []
        for a in s.stabilizing_agents.all():
            a_list.append(a)
        g_protein = only_gproteins(a_list)
        arrestin = only_arrestins(a_list)
        fusion = only_fusions(a_list)
        antibody = only_antibodies(a_list)

        r['method'] = methods[pdb_id] 
        r['resolution'] = "{0:.2g}".format(s.resolution)
        r['7tm_distance'] = s.distance
        r['g_protein'] = g_protein
        r['arrestin']  = arrestin
        r['fusion'] = fusion
        r['antibody'] = antibody

        r['ligand'] = "-"
        r['ligand_function'] = "-"
        r['ligand_type'] = "-"

        for l in s.ligands.all():
            r['ligand'] = l.ligand.name
            if len(r['ligand'])>20:
                r['ligand'] = r['ligand'][:20] + ".."
            r['ligand_function'] = l.ligand_role.name
            r['ligand_type'] = l.ligand.properities.ligand_type.name
        

        data_dict[pdb_id] = r
        data_table += "<tr> \
                        <td>{}</td> \
                        <td><span>{}</span></td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td>{}</td> \
                        <td data-sort='0'><input class='form-check-input pdb_selected' type='checkbox' value='' onclick='thisPDB(this);' representative='{}' long='{}'  id='{}'></td> \
                        </tr>\n".format(
                                        r['protein'],
                                        r['protein_long'],
                                        r['protein_family'],
                                        r['class'],
                                        r['species'],
                                        r['method'],
                                        pdb_id,
                                        r['resolution'],
                                        r['state'],
                                        r['active_class_contacts_fraction'],
                                        r['inactive_class_contacts_fraction'],
                                        r['contact_representative_score'],
                                        r['7tm_distance'],
                                        r['g_protein'],
                                        r['arrestin'],
                                        r['fusion'],
                                        r['antibody'],
                                        r['ligand'],
                                        r['ligand_function'],
                                        r['ligand_type'],
                                        r['contact_representative'],
                                        r['protein_long'],
                                        pdb_id
                                        )
    data_table += "</tbody></table>"
    return HttpResponse(data_table)

    # return render(request, 'contactnetwork/test.html', {'data_table':data_table})

def InteractionBrowserData(request):
    def gpcrdb_number_comparator(e1, e2):
            t1 = e1.split('x')
            t2 = e2.split('x')

            if e1 == e2:
                return 0

            if t1[0] == t2[0]:
                if t1[1] < t2[1]:
                    return -1
                else:
                    return 1

            if t1[0] < t2[0]:
                return -1
            else:
                return 1

    mode = 'single'
    # PDB files
    try:
        pdbs1 = request.GET.getlist('pdbs1[]')
        pdbs2 = request.GET.getlist('pdbs2[]')
    except IndexError:
        pdbs1 = []
    if pdbs1 and pdbs2:
        mode = 'double'
    # PDB files
    try:
        pdbs = request.GET.getlist('pdbs[]')
    except IndexError:
        pdbs = []

    pdbs = [pdb.lower() for pdb in pdbs]

    pdbs1 = [pdb.lower() for pdb in pdbs1]
    pdbs2 = [pdb.lower() for pdb in pdbs2]

    if pdbs1 and pdbs2:
        pdbs = pdbs1 + pdbs2

    if mode == 'single':
        pdbs1 = pdbs

    pdbs_upper = [pdb.upper() for pdb in pdbs]
    # Segment filters
    try:
        segments = request.GET.getlist('segments[]')
    except IndexError:
        segments = []

    # Interaction types
    try:
        i_types = request.GET.getlist('interaction_types[]')
    except IndexError:
        i_types = []

    segment_filter_res1 = Q()
    segment_filter_res2 = Q()

    if segments:
        segment_filter_res1 |= Q(interacting_pair__res1__protein_segment__slug__in=segments)
        segment_filter_res2 |= Q(interacting_pair__res2__protein_segment__slug__in=segments)

    i_types_filter = Q()
    if i_types:
        i_types_filter |= Q(interaction_type__in=i_types)

    cache_key = 'amino_acid_pair_conservation_{}'.format('001')
    class_pair_lookup = cache.get(cache_key)
    if class_pair_lookup==None or len(class_pair_lookup)==0:
        # Class pair conservation
        sum_proteins = Protein.objects.filter(family__slug__startswith='001',sequence_type__slug='wt',species__common_name='Human').count()
        residues = Residue.objects.filter(protein_conformation__protein__family__slug__startswith='001',
                                          protein_conformation__protein__sequence_type__slug='wt',
                                          protein_conformation__protein__species__common_name='Human',

                    ).exclude(generic_number=None).values('pk','sequence_number','generic_number__label','amino_acid','protein_conformation__protein__entry_name').all()
        r_pair_lookup = defaultdict(lambda: defaultdict(lambda: set()))
        for r in residues:
            r_pair_lookup[r['generic_number__label']][r['amino_acid']].add(r['protein_conformation__protein__entry_name'])
        class_pair_lookup = {}

        gen_keys = sorted(r_pair_lookup.keys(), key=functools.cmp_to_key(gpcrdb_number_comparator))
        for i,gen1 in enumerate(gen_keys):
            for gen2 in gen_keys[i:]:
                if gen1 == gen2:
                    continue
                pairs = {}
                v1 = r_pair_lookup[gen1]
                v2 = r_pair_lookup[gen2]
                coord = '{},{}'.format(gen1,gen2)
                for aa1 in v1.keys():
                    for aa2 in v2.keys():
                        pair = '{}{}'.format(aa1,aa2)
                        p1 = v1[aa1]
                        p2 = v2[aa2]
                        p = p1.intersection(p2)
                        if p:
                            class_pair_lookup[coord+pair] = round(100*len(p)/sum_proteins)
        cache.set(cache_key,class_pair_lookup,3600*24*7)

    # Get the relevant interactions
    interactions = list(Interaction.objects.filter(
        interacting_pair__referenced_structure__pdb_code__index__in=pdbs_upper
    ).values(
        'interaction_type',
        'interacting_pair__referenced_structure__pk',
        'interacting_pair__res1__pk',
        'interacting_pair__res2__pk',
    ).filter(interacting_pair__res1__pk__lt=F('interacting_pair__res2__pk')).filter(
        segment_filter_res1 & segment_filter_res2 #& i_types_filter
    ).distinct())

    # Interaction type sort - optimize by statically defining interaction type order
    order = ['ionic', 'polar', 'aromatic', 'hydrophobic', 'van-der-waals','None']
    interactions = sorted(interactions, key=lambda x: order.index(x['interaction_type']))

    data = {}
    data['interactions'] = {}
    data['pdbs'] = set()
    data['proteins'] = set()

    if mode == 'double':
        data['pdbs1'] = set()
        data['pdbs2'] = set()
        data['proteins1'] = set()
        data['proteins2'] = set()

    structures = Structure.objects.filter(pdb_code__index__in=pdbs_upper
                 ).select_related('protein_conformation__protein'
                 ).values('pk','pdb_code__index',
                        'protein_conformation__protein__parent__entry_name',
                        'protein_conformation__protein__entry_name')
    s_lookup = {}
    for s in structures:
        protein, pdb_name  = [s['protein_conformation__protein__parent__entry_name'],s['protein_conformation__protein__entry_name']]
        s_lookup[s['pk']] = [protein, pdb_name]
        # List PDB files that were found in dataset.
        data['pdbs'] |= {pdb_name}
        data['proteins'] |= {protein}

        # Populate the two groups lists
        if mode == 'double':
            if pdb_name in pdbs1:
                data['pdbs1'] |= {pdb_name}
                data['proteins1'] |= {protein}
            if pdb_name in pdbs2:
                data['pdbs2'] |= {pdb_name}
                data['proteins2'] |= {protein}

    # Create pair information for ALL pdbs for cache usage
    all_pdbs_pairs = cache.get("all_pdbs_aa_pairs")
    if not all_pdbs_pairs:
        # To save less, first figure out all possible interaction pairs
        interactions = list(Interaction.objects.all(
        ).values_list(
            'interacting_pair__res1__generic_number__label',
            'interacting_pair__res2__generic_number__label',
        ).filter(interacting_pair__res1__pk__lt=F('interacting_pair__res2__pk')).distinct())
        
        all_interaction_pairs = []
        all_interaction_residues = set()
        for i in interactions:
            all_interaction_pairs.append('{},{}'.format(i[0],i[1]))
            all_interaction_residues.add(i[0])
            all_interaction_residues.add(i[1])
        all_interaction_residues = sorted(list(all_interaction_residues), key=functools.cmp_to_key(gpcrdb_number_comparator))

        all_pdbs = list(Structure.objects.filter(refined=False).values_list('pdb_code__index', flat=True))
        all_pdbs = [x.lower() for x in all_pdbs]
        residues = Residue.objects.filter(protein_conformation__protein__entry_name__in=all_pdbs,
                    generic_number__label__in=all_interaction_residues).values('pk','sequence_number','generic_number__label','amino_acid','protein_conformation__protein__entry_name').all()
        
        r_lookup = {}
        r_pair_lookup = defaultdict(lambda: defaultdict(lambda: []))

        for r in residues:
            if r['generic_number__label'] not in all_interaction_residues:
                continue
            r_lookup[r['pk']] = r
            r_pair_lookup[r['generic_number__label']][r['amino_acid']].append(r['protein_conformation__protein__entry_name'])

        gen_keys = sorted(r_pair_lookup.keys(), key=functools.cmp_to_key(gpcrdb_number_comparator))
        all_pdbs_pairs = {}
        for i,gen1 in enumerate(all_interaction_residues):
            for gen2 in all_interaction_residues[i:]:
                if gen1 == gen2:
                    continue
                pairs = {}
                v1 = r_pair_lookup[gen1]
                v2 = r_pair_lookup[gen2]
                coord = '{},{}'.format(gen1,gen2)
                if coord not in all_interaction_pairs:
                    continue
                for aa1 in v1.keys():
                    for aa2 in v2.keys():
                        pair = '{}{}'.format(aa1,aa2)
                        p1 = set(v1[aa1])
                        p2 = set(v2[aa2])
                        p = list(p1.intersection(p2))
                        if p:
                            if coord not in all_pdbs_pairs:
                                all_pdbs_pairs[coord] = {}
                            all_pdbs_pairs[coord][pair] = p
        cache.set("all_pdbs_aa_pairs",all_pdbs_pairs,60*60*24*7) #Cache results
    else:
        residues = Residue.objects.filter(protein_conformation__protein__entry_name__in=pdbs
                ).exclude(generic_number=None).values('pk','sequence_number','generic_number__label','amino_acid','protein_conformation__protein__entry_name').all()
        r_lookup = {}
        r_pair_lookup = defaultdict(lambda: defaultdict(lambda: []))

        for r in residues:
            r_lookup[r['pk']] = r
            r_pair_lookup[r['generic_number__label']][r['amino_acid']].append(r['protein_conformation__protein__entry_name'])
         
    for i in interactions:
        s = i['interacting_pair__referenced_structure__pk']
        pdb_name = s_lookup[s][1]
        protein = s_lookup[s][0]
        res1 = r_lookup[i['interacting_pair__res1__pk']]
        res2 = r_lookup[i['interacting_pair__res2__pk']]
        res1_seq = res1['sequence_number']
        res2_seq = res2['sequence_number']
        res1_aa = res1['amino_acid']
        res2_aa = res2['amino_acid']
        res1_gen = res1['generic_number__label']
        res2_gen = res2['generic_number__label']
        model = i['interaction_type']

        res1 = res1_gen
        res2 = res2_gen

        if res1 < res2 or res1_seq < res2_seq:
            coord = str(res1) + ',' + str(res2)
        else:
            coord = str(res2) + ',' + str(res1)
            res1_aa, res2_aa = res2_aa, res1_aa

        if mode == 'double':
            if coord not in data['interactions']:
                data['interactions'][coord] = {'pdbs1':[], 'proteins1': [], 'pdbs2':[], 'proteins2': [], 'secondary1' : [], 'secondary2' : []}
            if pdb_name in pdbs1:
                if model in i_types:
                    if pdb_name not in data['interactions'][coord]['pdbs1']:
                        data['interactions'][coord]['pdbs1'].append(pdb_name)
                    if protein not in data['interactions'][coord]['proteins1']:
                        data['interactions'][coord]['proteins1'].append(protein)
                data['interactions'][coord]['secondary1'].append([model,res1_aa,res2_aa,pdb_name])
            if pdb_name in pdbs2:
                if model in i_types:
                    if pdb_name not in data['interactions'][coord]['pdbs2']:
                        data['interactions'][coord]['pdbs2'].append(pdb_name)
                    if protein not in data['interactions'][coord]['proteins2']:
                        data['interactions'][coord]['proteins2'].append(protein)
                data['interactions'][coord]['secondary2'].append([model,res1_aa,res2_aa,pdb_name])
        else:
            if coord not in data['interactions']:
                data['interactions'][coord] = {'pdbs':[], 'proteins': [], 'secondary': []}

            if pdb_name not in data['interactions'][coord]['pdbs']:
                data['interactions'][coord]['pdbs'].append(pdb_name)
            if protein not in data['interactions'][coord]['proteins']:
                data['interactions'][coord]['proteins'].append(protein)
            data['interactions'][coord]['secondary'].append([model,res1_aa,res2_aa,pdb_name])

    data['secondary'] = {}
    secondary_dict = {'set1':0 , 'set2':0, 'aa_pairs':OrderedDict()}
    secondary_dict_single = {'set':0 , 'aa_pairs':OrderedDict()}
    aa_pairs_dict = {'set1':0 , 'set2':0, 'class':{}}
    aa_pairs_dict_single = {'set':0, 'class':{}}
    delete_coords = []
    print(len(data['interactions']),'interactions2')
    for c,v in data['interactions'].items():
        if mode == 'double':
            if len(v["pdbs1"])+len(v["pdbs2"])==0:
                #empty
                delete_coords.append(c)
                continue
            data['secondary'][c] = OrderedDict()
            current = {}
            current["set1"] = pdbs1.copy()
            current["set2"] = pdbs2.copy()
            
            for setname,iset in [['set1','secondary1'],['set2','secondary2']]:
                for s in v[iset]:
                    i = s[0]
                    aa_pair = ''.join(s[1:3])
                    if s[3] in current[setname]:
                        #remove PDB from current set, to deduce those without an interaction
                        current[setname].remove(s[3])
                    if i not in data['secondary'][c]:
                        data['secondary'][c][i] = copy.deepcopy(secondary_dict)
                    data['secondary'][c][i][setname] += 1
                    if aa_pair not in data['secondary'][c][i]['aa_pairs']:
                        data['secondary'][c][i]['aa_pairs'][aa_pair] = copy.deepcopy(aa_pairs_dict)
                        # Count overall occurances in sets
                        aa1 = s[1]
                        aa2 = s[2]
                        gen1 = c.split(",")[0]
                        gen2 = c.split(",")[1]
                        pdbs_with_aa1 = r_pair_lookup[gen1][aa1]
                        pdbs_with_aa2 = r_pair_lookup[gen2][aa2]
                        pdbs_intersection = list(set(pdbs_with_aa1).intersection(pdbs_with_aa2))
                        pdbs1_with_pair = list(set(pdbs_intersection).intersection(pdbs1))
                        pdbs2_with_pair = list(set(pdbs_intersection).intersection(pdbs2))
                        data['secondary'][c][i]['aa_pairs'][aa_pair]['pair_set1'] = pdbs1_with_pair
                        data['secondary'][c][i]['aa_pairs'][aa_pair]['pair_set2'] = pdbs2_with_pair

                        if c+aa_pair in class_pair_lookup:
                            data['secondary'][c][i]['aa_pairs'][aa_pair]['class'] = class_pair_lookup[c+aa_pair]
                        else:
                            data['secondary'][c][i]['aa_pairs'][aa_pair]['class'] = "-"

                    data['secondary'][c][i]['aa_pairs'][aa_pair][setname] += 1

            i = 'None' ## Remember to also have this name in the "order" dict.
            data['secondary'][c][i] = copy.deepcopy(secondary_dict) 
            for setname in ['set1','set2']:
                data['secondary'][c][i][setname] += len(current[setname])
                for aa_pair, pdbs in all_pdbs_pairs[c].items():
                    if aa_pair not in data['secondary'][c][i]['aa_pairs']:
                        data['secondary'][c][i]['aa_pairs'][aa_pair] = copy.deepcopy(aa_pairs_dict)
                        if c+aa_pair in class_pair_lookup:
                            data['secondary'][c][i]['aa_pairs'][aa_pair]['class'] = class_pair_lookup[c+aa_pair]
                        else:
                            data['secondary'][c][i]['aa_pairs'][aa_pair]['class'] = "-"

                        aa1 = aa_pair[0]
                        aa2 = aa_pair[1]
                        gen1 = c.split(",")[0]
                        gen2 = c.split(",")[1]
                        pdbs_with_aa1 = r_pair_lookup[gen1][aa1]
                        pdbs_with_aa2 = r_pair_lookup[gen2][aa2]
                        pdbs_intersection = list(set(pdbs_with_aa1).intersection(pdbs_with_aa2))
                        pdbs1_with_pair = list(set(pdbs_intersection).intersection(pdbs1))
                        pdbs2_with_pair = list(set(pdbs_intersection).intersection(pdbs2))
                        data['secondary'][c][i]['aa_pairs'][aa_pair]['pair_set1'] = pdbs1_with_pair
                        data['secondary'][c][i]['aa_pairs'][aa_pair]['pair_set2'] = pdbs2_with_pair
                        

                    for pdb in current[setname]:
                        if pdb in pdbs:
                            # if pdb without interaction is in pdbs of aa_pair, add one.
                            data['secondary'][c][i]['aa_pairs'][aa_pair][setname] += 1
                    if setname == 'set2':
                        # if 2nd run
                        if data['secondary'][c][i]['aa_pairs'][aa_pair]["set1"] == 0 and data['secondary'][c][i]['aa_pairs'][aa_pair]["set2"] == 0:
                            del data['secondary'][c][i]['aa_pairs'][aa_pair] 

            # Order based on AA counts
            for i in data['secondary'][c].keys():
                data['secondary'][c][i]['aa_pairs'] = OrderedDict(sorted(data['secondary'][c][i]['aa_pairs'].items(), key=lambda x: x[1]["set1"]+x[1]["set2"], reverse = True))
            
            data['secondary'][c] = OrderedDict(sorted(data['secondary'][c].items(), key=lambda x: order.index(x[0])))
        elif mode =='single':
            # continue
            if len(v["pdbs"])==0:
                #empty
                delete_coords.append(c)
                continue
            data['secondary'][c] = OrderedDict()
            current = {}
            current["set"] = pdbs1.copy()
            setname = "set"
            for s in v['secondary']:
                i = s[0]
                aa_pair = ''.join(s[1:3])
                if s[3] in current[setname]:
                    #remove PDB from current set, to deduce those without an interaction
                    current[setname].remove(s[3])
                if i not in data['secondary'][c]:
                    data['secondary'][c][i] = copy.deepcopy(secondary_dict_single)
                data['secondary'][c][i][setname] += 1
                if aa_pair not in data['secondary'][c][i]['aa_pairs']:
                    data['secondary'][c][i]['aa_pairs'][aa_pair] = copy.deepcopy(aa_pairs_dict_single)
                    # Count overall occurances in sets
                    aa1 = s[1]
                    aa2 = s[2]
                    gen1 = c.split(",")[0]
                    gen2 = c.split(",")[1]
                    pdbs_with_aa1 = r_pair_lookup[gen1][aa1]
                    pdbs_with_aa2 = r_pair_lookup[gen2][aa2]
                    pdbs_intersection = list(set(pdbs_with_aa1).intersection(pdbs_with_aa2))
                    pdbs_with_pair = list(set(pdbs_intersection).intersection(pdbs1))
                    data['secondary'][c][i]['aa_pairs'][aa_pair]['pair_set'] = pdbs_with_pair

                    if c+aa_pair in class_pair_lookup:
                        data['secondary'][c][i]['aa_pairs'][aa_pair]['class'] = class_pair_lookup[c+aa_pair]
                    else:
                        data['secondary'][c][i]['aa_pairs'][aa_pair]['class'] = "-"

                data['secondary'][c][i]['aa_pairs'][aa_pair][setname] += 1
            
            i = 'None' ## Remember to also have this name in the "order" dict.
            data['secondary'][c][i] = copy.deepcopy(secondary_dict_single) 
            data['secondary'][c][i][setname] += len(current[setname])
            for aa_pair, pdbs in all_pdbs_pairs[c].items():
                if aa_pair not in data['secondary'][c][i]['aa_pairs']:
                    data['secondary'][c][i]['aa_pairs'][aa_pair] = copy.deepcopy(aa_pairs_dict_single)
                    if c+aa_pair in class_pair_lookup:
                        data['secondary'][c][i]['aa_pairs'][aa_pair]['class'] = class_pair_lookup[c+aa_pair]
                    else:
                        data['secondary'][c][i]['aa_pairs'][aa_pair]['class'] = "-"

                    aa1 = aa_pair[0]
                    aa2 = aa_pair[1]
                    gen1 = c.split(",")[0]
                    gen2 = c.split(",")[1]
                    pdbs_with_aa1 = r_pair_lookup[gen1][aa1]
                    pdbs_with_aa2 = r_pair_lookup[gen2][aa2]
                    pdbs_intersection = list(set(pdbs_with_aa1).intersection(pdbs_with_aa2))
                    pdbs_with_pair = list(set(pdbs_intersection).intersection(pdbs1))
                    data['secondary'][c][i]['aa_pairs'][aa_pair]['pair_set'] = pdbs_with_pair
                    

                for pdb in current[setname]:
                    if pdb in pdbs:
                        # if pdb without interaction is in pdbs of aa_pair, add one.
                        data['secondary'][c][i]['aa_pairs'][aa_pair][setname] += 1
                if data['secondary'][c][i]['aa_pairs'][aa_pair]["set"] == 0:
                    del data['secondary'][c][i]['aa_pairs'][aa_pair] 
    # print(delete_coords)
    for d in delete_coords:
        del data['interactions'][d]

    data['pdbs'] = list(data['pdbs'])
    data['proteins'] = list(data['proteins'])
    if mode == 'double':
        data['pdbs1'] = list(data['pdbs1'])
        data['pdbs2'] = list(data['pdbs2'])
        data['proteins1'] = list(data['proteins1'])
        data['proteins2'] = list(data['proteins2'])
    else:
        data['pdbs'] = list(data['pdbs'])

    return JsonResponse(data)

def DistanceDataGroups(request):
    def gpcrdb_number_comparator(e1, e2):
            t1 = e1.split('x')
            t2 = e2.split('x')

            if e1 == e2:
                return 0

            if t1[0] == t2[0]:
                if t1[1] < t2[1]:
                    return -1
                else:
                    return 1

            if t1[0] < t2[0]:
                return -1
            else:
                return 1

    # PDB files
    try:
        pdbs1 = request.GET.getlist('pdbs1[]')
        pdbs2 = request.GET.getlist('pdbs2[]')
    except IndexError:
        pdbs1 = []



    pdbs1 = [pdb.upper() for pdb in pdbs1]
    pdbs2 = [pdb.upper() for pdb in pdbs2]
    pdbs1_lower = [pdb.lower() for pdb in pdbs1]
    pdbs2_lower = [pdb.lower() for pdb in pdbs2]


    cache_key = ",".join(sorted(pdbs1)) + "_" + ",".join(sorted(pdbs2))
    cache_key = hashlib.md5(cache_key.encode('utf-8')).hexdigest()

    data = cache.get(cache_key)
    # data = None
    if data!=None:
        print('Result cached')
        return JsonResponse(data)

    # Segment filters
    try:
        segments = request.GET.getlist('segments[]')
    except IndexError:
        segments = []

    # Use generic numbers? Defaults to True.
    generic = True

    # Initialize response dictionary
    data = {}
    data['interactions'] = OrderedDict()
    data['pdbs'] = set()
    data['generic'] = generic
    data['segments'] = set()
    data['segment_map'] = {}
    # For Max schematics TODO -- make smarter.
    data['segment_map'] = {}
    data['aa_map'] = {}


    data['gn_map'] = OrderedDict()
    data['pos_map'] = OrderedDict()
    data['segment_map_full'] = OrderedDict()
    data['segment_map_full_gn'] = OrderedDict()
    data['generic_map_full'] = OrderedDict()


    list_of_gns = []

    excluded_segment = ['C-term','N-term','ICL1','ECL1','ECL2','ICL2','H8']
    segments = ProteinSegment.objects.all().exclude(slug__in = excluded_segment)
    proteins =  Protein.objects.filter(protein__entry_name__in=pdbs1_lower+pdbs2_lower).distinct().all()
    if len(proteins)>1:
        a = Alignment()
        a.ignore_alternative_residue_numbering_schemes = True;
        a.load_proteins(proteins)
        a.load_segments(segments) #get all segments to make correct diagrams
        # build the alignment data matrix
        a.build_alignment()
        # calculate consensus sequence + amino acid and feature frequency
        a.calculate_statistics()
        consensus = a.full_consensus

        for aa in consensus:
            if 'x' in aa.family_generic_number:
                list_of_gns.append(aa.family_generic_number)
                data['gn_map'][aa.family_generic_number] = aa.amino_acid
                data['pos_map'][aa.sequence_number] = aa.amino_acid
                data['segment_map_full_gn'][aa.family_generic_number] = aa.segment_slug
    else:
        rs = Residue.objects.filter(protein_conformation__protein=proteins[0]).prefetch_related('protein_segment','display_generic_number','generic_number')
        for r in rs:
            if (not generic):
                data['pos_map'][r.sequence_number] = r.amino_acid
                data['segment_map_full'][r.sequence_number] = r.protein_segment.slug
                if r.display_generic_number:
                    data['generic_map_full'][r.sequence_number] = r.short_display_generic_number()
            else:
                if r.generic_number:
                    list_of_gns.append(r.generic_number.label)
                    data['gn_map'][r.generic_number.label] = r.amino_acid
                    data['pos_map'][r.sequence_number] = r.amino_acid
                    data['segment_map_full_gn'][r.generic_number.label] = r.protein_segment.slug

    print('Start 1')
    start = time.time()
    dis1 = Distances()
    dis1.load_pdbs(pdbs1)
    dis1.fetch_and_calculate(with_arr = True)
    print('done fetching set 1',time.time()-start)
    # dis1.calculate_window(list_of_gns)
#    dis1.calculate()

    start = time.time()
    dis2 = Distances()
    dis2.load_pdbs(pdbs2)
    dis2.fetch_and_calculate(with_arr = True)
    # dis2.calculate_window(list_of_gns)
    #dis2.calculate()
    print('done fetching set 2',time.time()-start)

    diff = OrderedDict()
    from math import sqrt
    from scipy import stats

    # for d1 in dis1.stats_window_reduced:
    # for d1 in dis1.stats_window:

    start = time.time()
    total = {}
    common_labels = list(set(dis1.stats_key.keys()).intersection(dis2.stats_key.keys()))
    for label in common_labels:

        # Get variables
        d1, d2 = dis1.stats_key[label],dis2.stats_key[label]
        # Correct decimal
        mean1, mean2 = d1[1]/100,d2[1]/100
        std1,std2 = d1[2]/100,d2[2]/100
        var1,var2 = std1**2,std2**2
        n1, n2 = d1[4],d2[4]

        mean_diff = mean2-mean1

        # Save values for NGL calcs
        gn1,gn2 = label.split("_")
        if gn1 not in total:
            total[gn1] = {}
        if gn2 not in total:
            total[gn2] = {}
        total[gn1][gn2] = total[gn2][gn1] = round(mean_diff,1)
        # Make easier readable output
        d1[5] = [x / 100 for x in d1[5]]
        d2[5] = [x / 100 for x in d2[5]]
        individual_pdbs_1 = dict(zip(d1[6], d1[5]))
        individual_pdbs_2 = dict(zip(d2[6], d2[5]))

        if n1>1 and n2>1 and var1>0 and var2>0:
            ## T test to assess seperation of data (only if N>1 and there is variance)
            t_stat_welch = abs(mean1-mean2)/(sqrt( (var1/n1) + (var2/n2)  ))
            df = n1+n2 - 2
            p = 1 - stats.t.cdf(t_stat_welch,df=df)
        else:
            p = 0

        diff[label] = [round(mean_diff,1),[std1,std2],[mean1,mean2],[n1,n2],p,[individual_pdbs_1,individual_pdbs_2]]

    diff =  OrderedDict(sorted(diff.items(), key=lambda t: -abs(t[1][0])))

    print('done diff',time.time()-start)
    compared_stats = {}

    # Remove differences that seem statistically irrelevant
    for label,d in diff.items():
        if d[4]>0.05:
            #print(label,d)
            d[0] = 0
    print('done')

    # Dict to keep track of which residue numbers are in use
    number_dict = set()
    max_diff = 0
    #for d in dis.stats:
    for key,d in diff.items():

        # Ignore low means diff.
        if d[0]<0.5 and d[0]>-0.5:
            continue
        res1 = key.split("_")[0]
        res2 = key.split("_")[1]
        res1_seg = res1.split("x")[0]
        res2_seg = res2.split("x")[0]
        data['segment_map'][res1] = res1_seg
        data['segment_map'][res2] = res2_seg
        data['segments'] |= {res1_seg} | {res2_seg}

        # Populate the AA map
        if 1==2:
            #When showing pdbs
            if pdb_name not in data['aa_map']:
                data['aa_map'][pdb_name] = {}

        number_dict |= {res1, res2}

        if res1 < res2:
            coord = str(res1) + ',' + str(res2)
        else:
            coord = str(res2) + ',' + str(res1)

        # if pdb_name not in data['interactions'][coord]:
        #     data['interactions'][coord][pdb_name] = []

        if d:
            if len(data['interactions'])<10000:

                data['interactions'][coord] = d
            else:
                break

        if abs(d[0])>max_diff:
            max_diff = round(abs(d[0]))
        # data['sequence_numbers'] = sorted(number_dict)
    if (generic):
        data['sequence_numbers'] = sorted(number_dict, key=functools.cmp_to_key(gpcrdb_number_comparator))
    # else:
    #     data['sequence_numbers'] = sorted(number_dict)
        # break

    data['segments'] = list(data['segments'])
    data['pdbs'] = list(pdbs1+pdbs2)
    data['pdbs1'] = list(pdbs1)
    data['pdbs2'] = list(pdbs2)
    data['max_diff'] = max_diff
    print(len(data['interactions']),'len data')
    #total = {}
    start = time.time()
    ngl_max_diff = 0
    for gn1 in total.keys():
        vals = []
        for gn,val in total[gn1].items():
            if gn[0]!=gn1[0]:
                #if not same segment
                vals.append(val)
        total[gn1]['avg'] = round(float(sum(vals))/max(len(vals),1),1)
        if abs(total[gn1]['avg'])>ngl_max_diff:
            ngl_max_diff = round(abs(total[gn1]['avg']),1)

    print('done ngl',time.time()-start)
    data['ngl_data'] = total
    data['ngl_max_diff'] = ngl_max_diff
    print('send json')
    cache.set(cache_key,data,3600*24*7)
    return JsonResponse(data)


def ClusteringData(request):
    # PDB files
    try:
        pdbs = request.GET.getlist('pdbs[]')
    except IndexError:
        pdbs = []

    pdbs = [pdb.upper() for pdb in pdbs]

    # output dictionary
    data = {}

    # load all
    dis = Distances()
    dis.load_pdbs(pdbs)

    # common GNs
    common_gn = dis.fetch_common_gns_tm()
    all_gns = sorted(list(ResidueGenericNumber.objects.filter(scheme__slug='gpcrdb').all().values_list('label',flat=True)))
    pdb_distance_maps = {}
    pdb_gns = {}
    for pdb in pdbs:
        cache_key = "distanceMap-" + pdb

        # Cached?
        if cache.has_key(cache_key):
            cached_data = cache.get(cache_key)
            distance_map = cached_data["map"]
            structure_gn = cached_data["gns"]
        else:
            # grab raw distance data per structure
            temp = Distances()
            temp.load_pdbs([pdb])
            temp.fetch_distances_tm()

            structure_gn = list(Residue.objects.filter(protein_conformation__in=temp.pconfs) \
                .exclude(generic_number=None) \
                .exclude(generic_number__label__contains='8x') \
                .exclude(generic_number__label__contains='12x') \
                .exclude(generic_number__label__contains='23x') \
                .exclude(generic_number__label__contains='34x') \
                .exclude(generic_number__label__contains='45x') \
                .values_list('generic_number__label',flat=True))

            # create distance map
            distance_map = np.full((len(all_gns), len(all_gns)), 0.0)
            for i,res1 in enumerate(all_gns):
                for j in range(i+1, len(all_gns)):
                    # grab average value
                    res2 = all_gns[j]
                    if res1+"_"+res2 in temp.data:
                        distance_map[i][j] = temp.data[res1+"_"+res2][0]

            # store in cache
            store = {
                "map" : distance_map,
                "gns" : structure_gn

            }
            cache.set(cache_key, store, 60*60*24*14)
        pdb_gns[pdb] = structure_gn
        # Filtering indices to map to common_gns
        gn_indices = np.array([ all_gns.index(residue) for residue in common_gn ])
        pdb_distance_maps[pdb] = distance_map[gn_indices,:][:, gn_indices]

        if "average" in pdb_distance_maps:
            pdb_distance_maps["average"] +=  pdb_distance_maps[pdb]/len(pdbs)
        else:
            pdb_distance_maps["average"] =  pdb_distance_maps[pdb]/len(pdbs)

    # normalize and store distance map
    for pdb in pdbs:
        pdb_distance_maps[pdb] = np.nan_to_num(pdb_distance_maps[pdb]/pdb_distance_maps["average"])

        # # numpy way caused error on production server
        # i,j = pdb_distance_maps[pdb].shape
        # for i in range(i):
        #         for j in range(j):
        #             v = pdb_distance_maps[pdb][i][j]
        #             if v:
        #                 pdb_distance_maps[pdb][i][j] = v/pdb_distance_maps["average"][i][j]

    # calculate distance matrix
    distance_matrix = np.full((len(pdbs), len(pdbs)), 0.0)
    for i, pdb1 in enumerate(pdbs):
        for j in range(i+1, len(pdbs)):
            pdb2 = pdbs[j]
            # Get common GNs between two PDBs
            common_between_pdbs = sorted(list(set(pdb_gns[pdb1]).intersection(pdb_gns[pdb2])))
            # Get common between above set and the overall common set of GNs
            common_with_query_gns = sorted(list(set(common_gn).intersection(common_between_pdbs)))
            # Get the indices of positions that are shared between two PDBs
            gn_indices = np.array([ common_gn.index(residue) for residue in common_with_query_gns ])
            # Get distance between cells that have both GNs.
            distance = np.sum(np.absolute(pdb_distance_maps[pdb1][gn_indices,:][:, gn_indices] - pdb_distance_maps[pdb2][gn_indices,:][:, gn_indices]))
            distance_matrix[i, j] = distance
            distance_matrix[j, i] = distance


    # Collect structure annotations
    pdb_annotations = {}

    # Grab all annotations and all the ligand role when present in aggregates
    annotations = Structure.objects.filter(pdb_code__index__in=pdbs) \
                    .values_list('pdb_code__index','state__slug','protein_conformation__protein__parent__entry_name','protein_conformation__protein__parent__family__parent__name', \
                    'protein_conformation__protein__parent__family__parent__parent__name', 'protein_conformation__protein__parent__family__parent__parent__parent__name', 'structure_type__name') \
                    .annotate(arr=ArrayAgg('structureligandinteraction__ligand_role__slug', filter=Q(structureligandinteraction__annotated=True)))

    for an in annotations:
        pdb_annotations[an[0]] = list(an[1:])

        # Cleanup the aggregates as None values are introduced
        pdb_annotations[an[0]][6] = list(filter(None.__ne__, pdb_annotations[an[0]][6]))

    data['annotations'] = pdb_annotations

    # hierarchical clustering
    hclust = sch.linkage(ssd.squareform(distance_matrix), method='ward')
    tree = sch.to_tree(hclust, False)

    #inconsistency = sch.inconsistent(hclust)
    #inconsistency = sch.maxinconsts(hclust, inconsistency)
    silhouette_coefficient = {}
    getSilhouetteIndex(tree, distance_matrix, silhouette_coefficient)
    data['tree'] = getNewick(tree, "", tree.dist, pdbs, silhouette_coefficient)

    # Order distance_matrix by hclust
    N = len(distance_matrix)
    res_order = seriation(hclust, N, N + N-2)
    seriated_dist = np.zeros((N,N))
    a,b = np.triu_indices(N,k=1)
    seriated_dist[a,b] = distance_matrix[ [res_order[i] for i in a], [res_order[j] for j in b]]
    seriated_dist[b,a] = seriated_dist[a,b]

    data['distance_matrix'] = seriated_dist.tolist()
    data['dm_labels'] = [pdbs[i] for i in res_order]

    return JsonResponse(data)

# For reordering matrix based on h-tree
# Borrowed from https://gmarti.gitlab.io/ml/2017/09/07/how-to-sort-distance-matrix.html
def seriation(Z,N,cur_index):
    '''
        input:
            - Z is a hierarchical tree (dendrogram)
            - N is the number of points given to the clustering process
            - cur_index is the position in the tree for the recursive traversal
        output:
            - order implied by the hierarchical tree Z

        seriation computes the order implied by a hierarchical tree (dendrogram)
    '''
    if cur_index < N:
        return [cur_index]
    else:
        left = int(Z[cur_index-N,0])
        right = int(Z[cur_index-N,1])
        return (seriation(Z,N,left) + seriation(Z,N,right))

def getNewick(node, newick, parentdist, leaf_names, silhouette_coefficient):
    if node.is_leaf():
        return "%s:%.2f%s" % (leaf_names[node.id], parentdist - node.dist, newick)
    else:
        si_node = silhouette_coefficient[node.id]
        if len(newick) > 0:
            newick = ")%.2f:%.2f%s" % (si_node, parentdist - node.dist, newick)
        else:
            newick = ");"
        newick = getNewick(node.get_left(), newick, node.dist, leaf_names, silhouette_coefficient)
        newick = getNewick(node.get_right(), ",%s" % (newick), node.dist, leaf_names, silhouette_coefficient)
        newick = "(%s" % (newick)
        return newick

def getSilhouetteIndex(node, distance_matrix, results):
    # set rootnode (DEBUG purposes)
    if node.id not in results:
        results[node.id] = 0

    if not node.is_leaf():
        # get list of indices cluster left (A)
        a = node.get_left().pre_order(lambda x: x.id)

        # get list of indices cluster right (B)
        b = node.get_right().pre_order(lambda x: x.id)

        if len(a) > 1:
            # calculate average Si - cluster A
            si_a = calculateSilhouetteIndex(distance_matrix, a, b)
            results[node.get_left().id] = si_a

            getSilhouetteIndex(node.get_left(), distance_matrix, results)

        if len(b) > 1:
            # calculate average Si - cluster B
            si_b = calculateSilhouetteIndex(distance_matrix, b, a)
            results[node.get_right().id] = si_b

            getSilhouetteIndex(node.get_right(), distance_matrix, results)

# Implementation based on Rousseeuw, P.J. J. Comput. Appl. Math. 20 (1987): 53-65
def calculateSilhouetteIndex(distance_matrix, a, b):
    si = 0
    for i in a:
        # calculate ai - avg distance within cluster
        ai = 0
        for j in a:
            if i != j:
                ai += distance_matrix[i,j]/(len(a)-1)

        # calculate bi - avg distance to closest cluster
        bi = 0
        for j in b:
            bi += distance_matrix[i,j]/len(b)

        # silhouette index (averaged)
        si += (bi-ai)/max(ai,bi)/len(a)

    return si


def DistanceData(request):
    def gpcrdb_number_comparator(e1, e2):
            t1 = e1.split('x')
            t2 = e2.split('x')

            if e1 == e2:
                return 0

            if t1[0] == t2[0]:
                if t1[1] < t2[1]:
                    return -1
                else:
                    return 1

            if t1[0] < t2[0]:
                return -1
            else:
                return 1

    # PDB files
    try:
        pdbs = request.GET.getlist('pdbs[]')
    except IndexError:
        pdbs = []

    pdbs = [pdb.upper() for pdb in pdbs]
    pdbs_lower = [pdb.lower() for pdb in pdbs]

    cache_key = ",".join(sorted(pdbs))
    cache_key = hashlib.md5(cache_key.encode('utf-8')).hexdigest()

    data = cache.get(cache_key)
    # data = None
    if data!=None:
        print('Result cached')
        return JsonResponse(data)

    # Segment filters
    try:
        segments = request.GET.getlist('segments[]')
    except IndexError:
        segments = []

    # Use generic numbers? Defaults to True.
    generic = True

    # Initialize response dictionary
    data = {}
    data['interactions'] = OrderedDict()
    data['pdbs'] = set()
    data['generic'] = generic
    data['segments'] = set()
    data['segment_map'] = {}
    # For Max schematics TODO -- make smarter.
    data['segment_map'] = {}
    data['aa_map'] = {}


    data['gn_map'] = OrderedDict()
    data['pos_map'] = OrderedDict()
    data['segment_map_full'] = OrderedDict()
    data['segment_map_full_gn'] = OrderedDict()
    data['generic_map_full'] = OrderedDict()

    dis = Distances()
    dis.load_pdbs(pdbs)
    start = time.time()
    dis.fetch_and_calculate(with_arr = True)
    print('done fetching',time.time()-start)
    # dis.calculate_window()

    excluded_segment = ['C-term','N-term']
    segments = ProteinSegment.objects.all().exclude(slug__in = excluded_segment)
    proteins =  Protein.objects.filter(protein__entry_name__in=pdbs_lower).distinct().all()

    start = time.time()
    list_of_gns = []
    if len(proteins)>1:
        a = Alignment()
        a.ignore_alternative_residue_numbering_schemes = True;
        a.load_proteins(proteins)
        a.load_segments(segments) #get all segments to make correct diagrams
        # build the alignment data matrix
        a.build_alignment()
        # calculate consensus sequence + amino acid and feature frequency
        a.calculate_statistics()
        consensus = a.full_consensus

        for aa in consensus:
            if 'x' in aa.family_generic_number:
                list_of_gns.append(aa.family_generic_number)
                data['gn_map'][aa.family_generic_number] = aa.amino_acid
                data['pos_map'][aa.sequence_number] = aa.amino_acid
                data['segment_map_full_gn'][aa.family_generic_number] = aa.segment_slug
    else:
        rs = Residue.objects.filter(protein_conformation__protein=proteins[0]).prefetch_related('protein_segment','display_generic_number','generic_number')
        for r in rs:
            if (not generic):
                data['pos_map'][r.sequence_number] = r.amino_acid
                data['segment_map_full'][r.sequence_number] = r.protein_segment.slug
                if r.display_generic_number:
                    data['generic_map_full'][r.sequence_number] = r.short_display_generic_number()
            else:
                if r.generic_number:
                    list_of_gns.append(r.generic_number.label)
                    data['gn_map'][r.generic_number.label] = r.amino_acid
                    data['pos_map'][r.sequence_number] = r.amino_acid
                    data['segment_map_full_gn'][r.generic_number.label] = r.protein_segment.slug

    print('done alignment',time.time()-start)
    # Dict to keep track of which residue numbers are in use
    number_dict = set()
    max_dispersion = 0
    start = time.time()
    for d in dis.stats:
        # print(d)
        res1 = d[0].split("_")[0]
        res2 = d[0].split("_")[1]
        res1_seg = res1.split("x")[0]
        res2_seg = res2.split("x")[0]
        data['segment_map'][res1] = res1_seg
        data['segment_map'][res2] = res2_seg
        data['segments'] |= {res1_seg} | {res2_seg}

        # Populate the AA map
        if 1==2:
            #When showing pdbs
            if pdb_name not in data['aa_map']:
                data['aa_map'][pdb_name] = {}

        number_dict |= {res1, res2}

        if res1 < res2:
            coord = str(res1) + ',' + str(res2)
        else:
            coord = str(res2) + ',' + str(res1)


        # if pdb_name not in data['interactions'][coord]:
        #     data['interactions'][coord][pdb_name] = []
        if len(pdbs) > 1:
            if d[3]:
                # correct data decimal
                d[5] = [x / 100 for x in d[5]]
                # Make easier readable output
                individual_pdbs = dict(zip(d[6], d[5]))

                if len(data['interactions'])<2000:
                    data['interactions'][coord] = [round(d[1])/100,round(d[3],3),individual_pdbs]
                else:
                    break

                if d[3]>max_dispersion:
                    max_dispersion = round(d[3],3)
        else:
            if d[1]:
                if len(data['interactions'])<2000:
                    data['interactions'][coord] = [round(d[1])/100,round(d[1],3)/100,d[-1]]
                else:
                    break

                if d[1]>max_dispersion*100:
                    max_dispersion = round(d[1],3)/100
        # data['sequence_numbers'] = sorted(number_dict)
    if (generic):
        data['sequence_numbers'] = sorted(number_dict, key=functools.cmp_to_key(gpcrdb_number_comparator))
    # else:
    #     data['sequence_numbers'] = sorted(number_dict)
        # break

    data['segments'] = list(data['segments'])
    data['pdbs'] = list(pdbs)
    data['max_dispersion'] = max_dispersion

    print('done data prep',time.time()-start)
    total = {}
    ngl_max_diff = 0
    for i,gn1 in enumerate(list_of_gns):
        if gn1 not in total:
            total[gn1] = {}
        for gn2 in list_of_gns[i:]:
            if gn2 not in total:
                total[gn2] = {}
            label = "{}_{}".format(gn1,gn2)
            if label in dis.stats_key:
                value = dis.stats_key[label][3]
                total[gn1][gn2] =  value
                total[gn2][gn1] =  value
        vals = []
        for gn,val in total[gn1].items():
            if gn[0]!=gn1[0]:
                #if not same segment
                vals.append(val)
        total[gn1]['avg'] = round(float(sum(vals))/max(len(vals),1),3)**2
        if abs(total[gn1]['avg'])>ngl_max_diff:
            ngl_max_diff = round(abs(total[gn1]['avg']),3)

    data['ngl_data'] = total
    data['ngl_max_diff'] = ngl_max_diff

    # Cache result 7 days
    cache.set(cache_key,data,3600*24*7)
    return JsonResponse(data)

def InteractionData(request):
    def gpcrdb_number_comparator(e1, e2):
            t1 = e1.split('x')
            t2 = e2.split('x')

            if e1 == e2:
                return 0

            if t1[0] == t2[0]:
                if t1[1] < t2[1]:
                    return -1
                else:
                    return 1

            if t1[0] < t2[0]:
                return -1
            else:
                return 1

    # PDB files
    try:
        pdbs = request.GET.getlist('pdbs[]')
    except IndexError:
        pdbs = []

    pdbs = [pdb.lower() for pdb in pdbs]

    # Segment filters
    try:
        segments = request.GET.getlist('segments[]')
    except IndexError:
        segments = []

    # Interaction types
    try:
        i_types = request.GET.getlist('interaction_types[]')
    except IndexError:
        i_types = []

    # Use generic numbers? Defaults to True.
    generic = True
    try:
        generic_string = request.GET.get('generic')
        if generic_string in ['false', 'False', 'FALSE', '0']:
            generic = False
    except IndexError:
        pass

    segment_filter_res1 = Q()
    segment_filter_res2 = Q()

    if segments:
        segment_filter_res1 |= Q(interacting_pair__res1__protein_segment__slug__in=segments)
        segment_filter_res2 |= Q(interacting_pair__res2__protein_segment__slug__in=segments)

    i_types_filter = Q()
    if i_types:
        i_types_filter |= Q(interaction_type__in=i_types)

    # Get the relevant interactions
    interactions = Interaction.objects.filter(
        interacting_pair__referenced_structure__protein_conformation__protein__entry_name__in=pdbs
    ).values(
        'interacting_pair__referenced_structure__protein_conformation__protein__entry_name',
        'interacting_pair__res1__amino_acid',
        'interacting_pair__res2__amino_acid',
        'interacting_pair__res1__sequence_number',
        'interacting_pair__res1__generic_number__label',
        'interacting_pair__res1__protein_segment__slug',
        'interacting_pair__res2__sequence_number',
        'interacting_pair__res2__generic_number__label',
        'interacting_pair__res2__protein_segment__slug',
        'interaction_type',
    ).filter(
        segment_filter_res1 & segment_filter_res2 & i_types_filter
    )

    # Interaction type sort - optimize by statically defining interaction type order
    order = ['ionic', 'polar', 'aromatic', 'hydrophobic', 'van-der-waals']
    interactions = sorted(interactions, key=lambda x: order.index(x['interaction_type']))

    # Initialize response dictionary
    data = {}
    data['interactions'] = {}
    data['pdbs'] = set()
    data['generic'] = generic
    data['segments'] = set()
    data['segment_map'] = {}
    # For Max schematics TODO -- make smarter.
    data['segment_map'] = {}
    data['aa_map'] = {}

    # Create a consensus sequence.

    excluded_segment = ['C-term','N-term']
    segments = ProteinSegment.objects.all().filter(proteinfamily='GPCR').exclude(slug__in = excluded_segment)
    proteins =  Protein.objects.filter(protein__entry_name__in=pdbs).all()

    data['gn_map'] = OrderedDict()
    data['pos_map'] = OrderedDict()
    data['segment_map_full'] = OrderedDict()
    data['segment_map_full_gn'] = OrderedDict()
    data['generic_map_full'] = OrderedDict()

    if len(proteins)>1:
        a = Alignment()
        a.ignore_alternative_residue_numbering_schemes = True;
        a.load_proteins(proteins)
        a.load_segments(segments) #get all segments to make correct diagrams
        # build the alignment data matrix
        a.build_alignment()
        # calculate consensus sequence + amino acid and feature frequency
        a.calculate_statistics()
        consensus = a.full_consensus

        for aa in consensus:
            if 'x' in aa.family_generic_number:
                data['gn_map'][aa.family_generic_number] = aa.amino_acid
                data['pos_map'][aa.sequence_number] = aa.amino_acid
                data['segment_map_full_gn'][aa.family_generic_number] = aa.segment_slug
    else:
        rs = Residue.objects.filter(protein_conformation__protein=proteins[0]).prefetch_related('protein_segment','display_generic_number','generic_number')
        for r in rs:
            if (not generic):
                data['pos_map'][r.sequence_number] = r.amino_acid
                data['segment_map_full'][r.sequence_number] = r.protein_segment.slug
                if r.display_generic_number:
                    data['generic_map_full'][r.sequence_number] = r.short_display_generic_number()

    for i in interactions:
        pdb_name = i['interacting_pair__referenced_structure__protein_conformation__protein__entry_name']
        if not pdb_name in data['pdbs']:
            data['pdbs'].add(pdb_name)

    # Map from ordinary residue numbers to generic where available
    if (not generic):
        data['generic_map'] = {}

    # Dict to keep track of which residue numbers are in use
    number_dict = set()

    for i in interactions:
        pdb_name = i['interacting_pair__referenced_structure__protein_conformation__protein__entry_name']
        res1_seq = i['interacting_pair__res1__sequence_number']
        res2_seq = i['interacting_pair__res2__sequence_number']
        res1_gen = i['interacting_pair__res1__generic_number__label']
        res2_gen = i['interacting_pair__res2__generic_number__label']
        res1_seg = i['interacting_pair__res1__protein_segment__slug']
        res2_seg = i['interacting_pair__res2__protein_segment__slug']
        res1_aa = i['interacting_pair__res1__amino_acid']
        res2_aa = i['interacting_pair__res2__amino_acid']
        model = i['interaction_type']

        if generic and (not res1_gen or not res2_gen):
            continue

        # List PDB files that were found in dataset.
        data['pdbs'] |= {pdb_name}

        # Numbering convention
        res1 = res1_seq
        res2 = res2_seq

        if generic:
            res1 = res1_gen
            res2 = res2_gen

        if not generic and res1_gen:
            data['generic_map'][res1] = res1_gen

        if not generic and res2_gen:
            data['generic_map'][res2] = res2_gen

        # List which segments are available.
        data['segment_map'][res1] = res1_seg
        data['segment_map'][res2] = res2_seg
        data['segments'] |= {res1_seg} | {res2_seg}

        # Populate the AA map
        if pdb_name not in data['aa_map']:
            data['aa_map'][pdb_name] = {}

        data['aa_map'][pdb_name][res1] = res1_aa
        data['aa_map'][pdb_name][res2] = res2_aa

        number_dict |= {res1, res2}

        if res1 < res2:
            coord = str(res1) + ',' + str(res2)
        else:
            coord = str(res2) + ',' + str(res1)

        if coord not in data['interactions']:
            data['interactions'][coord] = {}

        if pdb_name not in data['interactions'][coord]:
            data['interactions'][coord][pdb_name] = []

        data['interactions'][coord][pdb_name].append(model)

    if (generic):
        data['sequence_numbers'] = sorted(number_dict, key=functools.cmp_to_key(gpcrdb_number_comparator))
    else:
        data['sequence_numbers'] = sorted(number_dict)

    data['segments'] = list(data['segments'])
    data['pdbs'] = list(data['pdbs'])

    return JsonResponse(data)

def ServePDB(request, pdbname):
    structure=Structure.objects.filter(pdb_code__index=pdbname.upper())
    if structure.exists():
        structure=structure.get()
    else:
        quit() #quit!

    if structure.pdb_data is None:
        quit()

    only_gns = list(structure.protein_conformation.residue_set.exclude(generic_number=None).values_list('protein_segment__slug','sequence_number','generic_number__label').all())
    only_gn = []
    gn_map = []
    segments = {}
    for gn in only_gns:
        only_gn.append(gn[1])
        gn_map.append(gn[2])
        if gn[0] not in segments:
            segments[gn[0]] = []
        segments[gn[0]].append(gn[1])

    data = {}
    data['pdb'] = structure.pdb_data.pdb
    data['only_gn'] = only_gn
    data['gn_map'] = gn_map
    data['segments'] = segments
    data['chain'] = structure.preferred_chain
    # positioning data
    sv = StructureVectors.objects.filter(structure=structure)
    if sv.exists():
        sv = sv.get()
        data['translation'] = sv.translation
        data['center_axis'] = sv.center_axis

    return JsonResponse(data)

def StateContacts(request):
    contacts = ConsensusInteraction.objects.filter(state_specific = True).prefetch_related('gn1','gn2','state','protein_class').all()
    context = {}
    context['contacts'] = contacts
    return render(request, 'contactnetwork/state_contacts.html', context)


