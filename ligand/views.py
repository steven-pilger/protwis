from django.db.models import Count, Avg, Min, Max
from collections import defaultdict
from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import TemplateView, View

from common.models import ReleaseNotes
from common.phylogenetic_tree import PhylogeneticTreeGenerator
from common.selection import Selection, SelectionItem
from ligand.models import Ligand, AssayExperiment, LigandProperities, LigandVendorLink
from protein.models import Protein, Species, ProteinFamily

from copy import deepcopy
import itertools
import json
    
class LigandBrowser(TemplateView):
    """
    Per target summary of ligands.
    """
    template_name = 'ligand_browser.html'

    def get_context_data (self, **kwargs):

        context = super(LigandBrowser, self).get_context_data(**kwargs)

        ligands = AssayExperiment.objects.values(
            'protein__entry_name', 
            'protein__species__common_name',
            'protein__family__name',
            'protein__family__parent__name',
            'protein__family__parent__parent__name',
            'protein__family__parent__parent__parent__name',
            'protein__species__common_name'
            ).annotate(num_ligands=Count('ligand', distinct=True))

        context['ligands'] = ligands

        return context


def LigandDetails(request, ligand_id):
    """
    The details of a ligand record. Lists all the assay experiments for a given ligand.
    """
    ligand_records = AssayExperiment.objects.filter(
        ligand__properities__web_links__index=ligand_id
        ).order_by('protein__entry_name')

    record_count = ligand_records.values(
        'protein',
        ).annotate(num_records = Count('protein__entry_name')
                   ).order_by('protein__entry_name')
    
    
    ligand_data = []

    for record in record_count:
        per_target_data = ligand_records.filter(protein=record['protein'])
        protein_details = Protein.objects.get(pk=record['protein'])

        """
        A dictionary of dictionaries with a list of values.
        Assay_type
        |
        ->  Standard_type [list of values]
        """
        tmp = defaultdict(lambda: defaultdict(list))
        tmp_count = 0
        for data_line in per_target_data:
            tmp[data_line.assay_type][data_line.standard_type].append(data_line.standard_value)
            tmp_count += 1

        #Flattened list of lists of dict values
        values = list(itertools.chain(*[itertools.chain(*tmp[x].values()) for x in tmp.keys()]))
        
        ligand_data.append({
            'protein_name': protein_details.entry_name,
            'receptor_family': protein_details.family.parent.name,
            'ligand_type': protein_details.get_protein_family(),
            'class': protein_details.get_protein_class(),
            'record_count': tmp_count,
            'assay_type': ', '.join(tmp.keys()),
            #Flattened list of lists of dict keys:
            'value_types': ', '.join(itertools.chain(*(list(tmp[x]) for x in tmp.keys()))),
            'low_value': min(values),
            'average_value': sum(values)/len(values),
            'standard_units': ', '.join(list(set([x.standard_units for x in per_target_data])))
            })

    context = {'ligand_data': ligand_data, 'ligand':ligand_id}
    
    return render(request, 'ligand_details.html', context)


def TargetDetailsCompact(request, **kwargs):
    if 'slug' in kwargs:
        slug = kwargs['slug']
        if slug.count('_') == 0 :
            ps = AssayExperiment.objects.filter(protein__family__parent__parent__parent__slug=slug, ligand__properities__web_links__web_resource__slug = 'chembl_ligand')
        elif slug.count('_') == 1 and len(slug) == 7:
            ps = AssayExperiment.objects.filter(protein__family__parent__parent__slug=slug, ligand__properities__web_links__web_resource__slug = 'chembl_ligand')
        elif slug.count('_') == 2:
            ps = AssayExperiment.objects.filter(protein__family__parent__slug=slug, ligand__properities__web_links__web_resource__slug = 'chembl_ligand')
        #elif slug.count('_') == 3:
        elif slug.count('_') == 1 and len(slug) != 7:
            ps = AssayExperiment.objects.filter(protein__entry_name = slug, ligand__properities__web_links__web_resource__slug = 'chembl_ligand')
    
        if slug.count('_') == 1 and len(slug) == 7:
            f = ProteinFamily.objects.get(slug=slug)      
        else:
            f = slug

        context = {
            'target':f
            }
    else:
        simple_selection = request.session.get('selection', False)
        selection = Selection()
        if simple_selection:
            selection.importer(simple_selection)
        if selection.targets != []:
            prot_ids = [x.item.id for x in selection.targets]
            ps = AssayExperiment.objects.filter(protein__in=prot_ids, ligand__properities__web_links__web_resource__slug = 'chembl_ligand')
            context = {
                'target': ', '.join([x.item.entry_name for x in selection.targets])
                }

    ps = ps.prefetch_related('protein','ligand__properities__web_links__web_resource','ligand__properities__vendors__vendor')
    d = {}
    for p in ps:
        if p.ligand not in d:
            d[p.ligand] = {}
        if p.protein not in d[p.ligand]:
             d[p.ligand][p.protein] = []
        d[p.ligand][p.protein].append(p)
    ligand_data = []
    for lig, records  in d.items():

        links = lig.properities.web_links.all()
        chembl_id = [x for x in links if x.web_resource.slug=='chembl_ligand'][0].index

        vendors = lig.properities.vendors.all()
        purchasability = 'No'
        for v in vendors:
            if v.vendor.name not in ['ZINC', 'ChEMBL', 'BindingDB', 'SureChEMBL', 'eMolecules', 'MolPort', 'PubChem']:
                purchasability = 'Yes'

        for record, vals in records.items():
            per_target_data = vals
            protein_details = record

            """
            A dictionary of dictionaries with a list of values.
            Assay_type
            |
            ->  Standard_type [list of values]
            """
            tmp = defaultdict(list)
            tmp_count = 0
            for data_line in per_target_data:
                tmp["Bind" if data_line.assay_type == 'b' else "Funct"].append(data_line.pchembl_value)
                tmp_count += 1
            values = list(itertools.chain(*tmp.values()))
            ligand_data.append({
                'ligand_id': chembl_id,
                'protein_name': protein_details.entry_name,
                'species': protein_details.species.common_name,
                'record_count': tmp_count,
                'assay_type': ', '.join(tmp.keys()),
                'purchasability': purchasability,
                #Flattened list of lists of dict keys:
                'low_value': min(values),
                'average_value': sum(values)/len(values),
                'high_value': max(values),
                'standard_units': ', '.join(list(set([x.standard_units for x in per_target_data]))),
                'smiles': lig.properities.smiles,
                'mw': lig.properities.mw,
                'rotatable_bonds': lig.properities.rotatable_bonds,
                'hdon': lig.properities.hdon,
                'hacc': lig.properities.hacc,
                'logp': lig.properities.logp,
                })
    context['ligand_data'] = ligand_data
    
    return render(request, 'target_details_compact.html', context)

def TargetDetails(request, **kwargs):

    if 'slug' in kwargs:
        slug = kwargs['slug']
        if slug.count('_') == 0 :
            ps = AssayExperiment.objects.filter(protein__family__parent__parent__parent__slug=slug, ligand__properities__web_links__web_resource__slug = 'chembl_ligand')
        elif slug.count('_') == 1 and len(slug) == 7:
            ps = AssayExperiment.objects.filter(protein__family__parent__parent__slug=slug, ligand__properities__web_links__web_resource__slug = 'chembl_ligand')
        elif slug.count('_') == 2:
            ps = AssayExperiment.objects.filter(protein__family__parent__slug=slug, ligand__properities__web_links__web_resource__slug = 'chembl_ligand')
        #elif slug.count('_') == 3:
        elif slug.count('_') == 1 and len(slug) != 7:
            ps = AssayExperiment.objects.filter(protein__entry_name = slug, ligand__properities__web_links__web_resource__slug = 'chembl_ligand')
    
        if slug.count('_') == 1 and len(slug) == 7:
            f = ProteinFamily.objects.get(slug=slug)      
        else:
            f = slug

        context = {
            'target':f
            }
    else:
        simple_selection = request.session.get('selection', False)
        selection = Selection()
        if simple_selection:
            selection.importer(simple_selection)
        if selection.targets != []:
            prot_ids = [x.item.id for x in selection.targets]
            ps = AssayExperiment.objects.filter(protein__in=prot_ids, ligand__properities__web_links__web_resource__slug = 'chembl_ligand')
            context = {
                'target': ', '.join([x.item.entry_name for x in selection.targets])
                }
    ps = ps.values('standard_type',
                'standard_relation',
                'standard_value',
                'assay_description',
                'assay_type',
                #'standard_units',
                'pchembl_value',
                'ligand__id',
                'ligand__properities_id',
                'ligand__properities__web_links__index',
                #'ligand__properities__vendors__vendor__name',
                'protein__species__common_name',
                'protein__entry_name',
                'ligand__properities__mw',
                'ligand__properities__logp',
                'ligand__properities__rotatable_bonds',
                'ligand__properities__smiles',
                'ligand__properities__hdon',
                'ligand__properities__hacc','protein'
                ).annotate(num_targets = Count('protein__id', distinct=True))
    for record in ps:
        record['purchasability'] = 'Yes' if len(LigandVendorLink.objects.filter(lp=record['ligand__properities_id']).exclude(vendor__name__in=['ZINC', 'ChEMBL', 'BindingDB', 'SureChEMBL', 'eMolecules', 'MolPort', 'PubChem'])) > 0 else 'No'

    context['proteins'] = ps

    return render(request, 'target_details.html', context)


def TargetPurchasabilityDetails(request, **kwargs):

    simple_selection = request.session.get('selection', False)
    selection = Selection()
    if simple_selection:
        selection.importer(simple_selection)
    if selection.targets != []:
        prot_ids = [x.item.id for x in selection.targets]
        ps = AssayExperiment.objects.filter(protein__in=prot_ids, ligand__properities__web_links__web_resource__slug = 'chembl_ligand')
        context = {
            'target': ', '.join([x.item.entry_name for x in selection.targets])
            }

    ps = ps.values('standard_type',
                'standard_relation',
                'standard_value',
                'assay_description',
                'assay_type',
                'standard_units',
                'pchembl_value',
                'ligand__id',
                'ligand__properities_id',
                'ligand__properities__web_links__index',
                'ligand__properities__vendors__vendor__id',
                'ligand__properities__vendors__vendor__name',
                'protein__species__common_name',
                'protein__entry_name',
                'ligand__properities__mw',
                'ligand__properities__logp',
                'ligand__properities__rotatable_bonds',
                'ligand__properities__smiles',
                'ligand__properities__hdon',
                'ligand__properities__hacc','protein'
                ).annotate(num_targets = Count('protein__id', distinct=True))
    purchasable = []
    for record in ps:
        try:
            if record['ligand__properities__vendors__vendor__name'] in ['ZINC', 'ChEMBL', 'BindingDB', 'SureChEMBL', 'eMolecules', 'MolPort', 'PubChem', 'IUPHAR/BPS Guide to PHARMACOLOGY']:
                continue
            tmp = LigandVendorLink.objects.filter(vendor=record['ligand__properities__vendors__vendor__id'], lp=record['ligand__properities_id'])[0]
            record['vendor_id'] = tmp.vendor_external_id
            record['vendor_link'] = tmp.url
            purchasable.append(record)
        except:
            continue

    context['proteins'] = purchasable




    return render(request, 'target_purchasability_details.html', context)


class LigandStatistics(TemplateView):
    """
    Per class statistics of known ligands.
    """

    template_name = 'ligand_statistics.html'

    def get_context_data (self, **kwargs):

        context = super().get_context_data(**kwargs)
        assays = AssayExperiment.objects.all().prefetch_related('protein__family__parent__parent__parent', 'protein__family')

        lig_count_dict = {}
        assays_lig = list(AssayExperiment.objects.all().values('protein__family__parent__parent__parent__name').annotate(c=Count('ligand',distinct=True)))
        for a in assays_lig:
            lig_count_dict[a['protein__family__parent__parent__parent__name']] = a['c']
        target_count_dict = {}
        assays_target = list(AssayExperiment.objects.all().values('protein__family__parent__parent__parent__name').annotate(c=Count('protein__family',distinct=True)))
        for a in assays_target:
            target_count_dict[a['protein__family__parent__parent__parent__name']] = a['c']

        prot_count_dict = {}
        proteins_count = list(Protein.objects.all().values('family__parent__parent__parent__name').annotate(c=Count('family',distinct=True)))
        for pf in proteins_count:
            prot_count_dict[pf['family__parent__parent__parent__name']] = pf['c']

        classes = ProteinFamily.objects.filter(slug__in=['001', '002', '003', '004', '005', '006']) #ugly but fast
        proteins = Protein.objects.all().prefetch_related('family__parent__parent__parent')
        ligands = []

        for fam in classes:
            if fam.name in lig_count_dict:
                lig_count = lig_count_dict[fam.name]
                target_count = target_count_dict[fam.name]
            else:
                lig_count = 0
                target_count = 0
            prot_count = prot_count_dict[fam.name]
            ligands.append({
                'name': fam.name,
                'num_ligands': lig_count,
                'avg_num_ligands': lig_count/prot_count,
                'target_percentage': target_count/prot_count*100,
                'target_count': target_count
                })
        lig_count_total = sum([x['num_ligands'] for x in ligands])
        prot_count_total = Protein.objects.filter(family__slug__startswith='00').all().distinct('family').count()
        target_count_total = sum([x['target_count'] for x in ligands])
        lig_total = {
            'num_ligands': lig_count_total,
            'avg_num_ligands': lig_count_total/prot_count_total,
            'target_percentage': target_count_total/prot_count_total*100,
            'target_count': target_count_total
            }
        #Elegant solution but kinda slow (6s querries):
        """
        ligands = AssayExperiment.objects.values(
            'protein__family__parent__parent__parent__name',
            'protein__family__parent__parent__parent',
            ).annotate(num_ligands=Count('ligand', distinct=True))
        for prot_class in ligands:
            class_subset = AssayExperiment.objects.filter(
                id=prot_class['protein__family__parent__parent__parent']).values(
                    'protein').annotate(
                        avg_num_ligands=Avg('ligand', distinct=True), 
                        p_count=Count('protein')
                        )
            prot_class['avg_num_ligands']=class_subset[0]['avg_num_ligands']
            prot_class['p_count']=class_subset[0]['p_count']

        """
        context['ligands_total'] = lig_total
        context['ligands_by_class'] = ligands

        context['release_notes'] = ReleaseNotes.objects.all()[0]

        tree = PhylogeneticTreeGenerator()
        class_a_data = tree.get_tree_data(ProteinFamily.objects.get(name='Class A (Rhodopsin)'))
        context['class_a_options'] = deepcopy(tree.d3_options)
        context['class_a_options']['anchor'] = 'class_a'
        context['class_a_options']['leaf_offset'] = 50
        context['class_a_options']['label_free'] = []
        context['class_a'] = json.dumps(class_a_data.get_nodes_dict('ligands'))
        class_b1_data = tree.get_tree_data(ProteinFamily.objects.get(name__startswith='Class B1 (Secretin)'))
        context['class_b1_options'] = deepcopy(tree.d3_options)
        context['class_b1_options']['anchor'] = 'class_b1'
        context['class_b1_options']['branch_trunc'] = 60
        context['class_b1_options']['label_free'] = [1,]
        context['class_b1'] = json.dumps(class_b1_data.get_nodes_dict('ligands'))
        class_b2_data = tree.get_tree_data(ProteinFamily.objects.get(name__startswith='Class B2 (Adhesion)'))
        context['class_b2_options'] = deepcopy(tree.d3_options)
        context['class_b2_options']['anchor'] = 'class_b2'
        context['class_b2_options']['label_free'] = [1,]
        context['class_b2'] = json.dumps(class_b2_data.get_nodes_dict('ligands'))
        class_c_data = tree.get_tree_data(ProteinFamily.objects.get(name__startswith='Class C (Glutamate)'))
        context['class_c_options'] = deepcopy(tree.d3_options)
        context['class_c_options']['anchor'] = 'class_c'
        context['class_c_options']['branch_trunc'] = 50
        context['class_c_options']['label_free'] = [1,]
        context['class_c'] = json.dumps(class_c_data.get_nodes_dict('ligands'))
        class_f_data = tree.get_tree_data(ProteinFamily.objects.get(name__startswith='Class F (Frizzled)'))
        context['class_f_options'] = deepcopy(tree.d3_options)
        context['class_f_options']['anchor'] = 'class_f'
        context['class_f_options']['label_free'] = [1,]
        context['class_f'] = json.dumps(class_f_data.get_nodes_dict('ligands'))
        class_t2_data = tree.get_tree_data(ProteinFamily.objects.get(name='Taste 2'))
        context['class_t2_options'] = deepcopy(tree.d3_options)
        context['class_t2_options']['anchor'] = 'class_t2'
        context['class_t2_options']['label_free'] = [1,]
        context['class_t2'] = json.dumps(class_t2_data.get_nodes_dict('ligands'))

        return context