# coding=utf-8

import sys
from functools import reduce
import operator
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.core.paginator import Paginator, InvalidPage, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.db import IntegrityError

from django.db.models import CharField, OneToOneField, ManyToManyField, ForeignKey, DateField, DateTimeField, TimeField, \
    TextField, OneToOneRel, ManyToManyRel, ManyToOneRel, IntegerField, FloatField, BigIntegerField, BinaryField

from spcc.models.old_model_meta import get_concrete_fields_with_model
from spmo.common import Common, DD
from spmo.strings.common import is_contain_chinese

import copy

co = Common()


def get_model_fields(model=None):
    '''
    获取model中所有的field对象
    :param model:
    :return:
    '''
    # field_objects = [ y[0] for y in model._meta.get_fields_with_model() ] #取得model中的全部field 对象
    # Django 1.8开始，get_fields_with_model函数还会返回其它modle字段，现改用get_concrete_fields_with_model函数
    field_objects = [y[0] for y in get_concrete_fields_with_model(model=model)]  # 取得model中的全部field 对象
    return field_objects


def get_model_all_files(model=None):
    '''
    获取model所有field对象，以及相关one2one，many2one等
    :param model:
    :return:
    '''
    return model._meta.get_fields()


def split_model_field(model=None):
    text_fields = []
    char_fields = []
    date_fields = []
    other_fields = []
    one2one_fields = []
    many2many_fields = []
    foreign_fields = []
    one2onerel_fields = []
    many2manyrel_fields = []
    many2onerel_fields = []
    int_fields = []
    bigint_fields = []
    binary_fields = []
    float_fields = []

    for f in get_model_all_files(model):
        if isinstance(f, CharField):
            char_fields.append(f)
        elif isinstance(f, OneToOneField):
            one2one_fields.append(f)
        elif isinstance(f, ManyToManyField):
            many2many_fields.append(f)
        elif isinstance(f, ForeignKey):
            foreign_fields.append(f)
        elif isinstance(f, DateTimeField) or isinstance(f, DateField) or isinstance(f, TimeField):
            date_fields.append(f)
        elif isinstance(f, TextField):
            text_fields.append(f)
        elif isinstance(f, OneToOneRel):
            one2onerel_fields.append(f)
        elif isinstance(f, ManyToManyRel):
            many2manyrel_fields.append(f)
        elif isinstance(f, ManyToOneRel):
            many2onerel_fields.append(f)
        elif isinstance(f, IntegerField):
            int_fields.append(f)
        elif isinstance(f, FloatField):
            float_fields.append(f)
        elif isinstance(f, BigIntegerField):
            bigint_fields.append(f)
        elif isinstance(f, BinaryField):
            binary_fields.append(f)
        else:
            other_fields.append(f)

    return {
        'text_fields': text_fields,
        'char_fields': char_fields,
        'date_fields': date_fields,
        'other_fields': other_fields,
        'one2one_fields': one2one_fields,
        'many2many_fields': many2many_fields,
        'foreign_fields': foreign_fields,
        'one2onerel_fields': one2onerel_fields,
        'many2manyrel_fields': many2manyrel_fields,
        'many2onerel_fields': many2onerel_fields,
        'int_fields': int_fields,
        'float_fields': float_fields,
        'bigint_fields': bigint_fields,
        'binary_fields': binary_fields,
    }


def get_filter_fields(model=None):
    r_fields = {}
    num_lookup_expr = ['exact', 'contains', 'icontains', 'gte', 'lte']
    txt_lookup_expr = ['exact', 'contains', 'icontains']

    s_fields = split_model_field(model=model)
    text_fields = s_fields.get('text_fields', [])
    char_fields = s_fields.get('char_fields', [])
    date_fields = s_fields.get('date_fields', [])
    other_fields = s_fields.get('other_fields', [])
    one2one_fields = s_fields.get('one2one_fields', [])
    many2many_fields = s_fields.get('many2many_fields', [])
    foreign_fields = s_fields.get('foreign_fields', [])
    one2onerel_fields = s_fields.get('one2onerel_fields', [])
    many2manyrel_fields = s_fields.get('many2manyrel_fields', [])
    many2onerel_fields = s_fields.get('many2onerel_fields', [])
    int_fields = s_fields.get('int_fields', [])
    bigint_fields = s_fields.get('bigint_fields', [])
    binary_fields = s_fields.get('binary_fields', [])
    float_fields = s_fields.get('float_fields', [])

    for nf in int_fields + bigint_fields + float_fields:
        r_fields[nf.name] = num_lookup_expr

    for tf in text_fields + char_fields + date_fields + other_fields:
        r_fields[tf.name] = txt_lookup_expr

    return r_fields


def get_q(do_model=None, search_str=None, q_field_pre=None, ):
    text_fields = []
    char_fields = []
    date_fields = []
    other_fields = []
    one2one_fields = []
    many2many_fields = []
    foreign_fields = []
    queries = []

    for f in get_model_fields(do_model):
        if isinstance(f, CharField):
            char_fields.append(f)
        elif isinstance(f, OneToOneField):
            one2one_fields.append(f)
        elif isinstance(f, ManyToManyField):
            many2many_fields.append(f)
        elif isinstance(f, ForeignKey):
            foreign_fields.append(f)
        elif isinstance(f, DateTimeField) or isinstance(f, DateField) or isinstance(f, TimeField):
            date_fields.append(f)
        elif isinstance(f, TextField):
            text_fields.append(f)
        else:
            other_fields.append(f)

    #
    # if is_contain_chinese(search_str):  # mysql的搜索时间字段不能使用中文关键词
    #     do_search_files = char_fields + text_fields
    # else:
    #     do_search_files = char_fields + text_fields

    do_search_files = char_fields + text_fields + other_fields

    for cf in do_search_files:
        if q_field_pre is not None:
            queries.append(Q(**{'%s__%s__icontains' % (q_field_pre, cf.name): search_str}))
        else:
            queries.append(Q(**{'%s__icontains' % cf.name: search_str}))

    do_r_fields = one2one_fields + foreign_fields + many2many_fields
    # for o in one2one_fields:
    #     print('------')
    #     print(o)

    # do_r_fields = one2one_fields + foreign_fields
    for rf in do_r_fields:
        r_model = rf.related_model
        if r_model in done_models:
            continue
        done_models.append(r_model)
        if q_field_pre is not None:
            n_q_field_pre = '%s__%s' % (q_field_pre, rf.name)
        else:
            n_q_field_pre = rf.name

        queries = queries + get_q(do_model=r_model, search_str=search_str, q_field_pre=n_q_field_pre)

    return queries


def get_qs(d_model, s_str, search_i={}):
    # global s_model
    s_model = d_model
    # global done_models
    done_models = []

    limit = {}
    s_q = []
    q_field_lookup = 'icontains'
    q_fields = []
    f_q = {}
    if isinstance(search_i, dict):
        if 'limit' in search_i:
            limit = search_i['limit']
        if 's_q' in search_i:
            s_q = search_i['s_q']
        if 'q_field_lookup' in search_i:
            q_field_lookup = search_i['q_field_lookup']
        if 'q_fields' in search_i:
            q_fields = search_i['q_fields']
        if 'f_q' in search_i:
            f_q = search_i['f_q']

    if isinstance(f_q, dict) and len(f_q) > 0:
        s_q2 = [Q(**{f_qi: f_q[f_qi]}) for f_qi in f_q.keys()]
    else:
        s_q2 = [Q(**{s_qi: s_str}) for s_qi in s_q]
    black_fields = []
    black_models = []
    r_depth_max = 5
    if isinstance(limit, dict):
        black_fields = limit.get('black_fields', ['id'])
        black_models = limit.get('black_models', ['userprofile', 'eventlog', ])
        r_depth_max = limit.get('r_depth_max', 5)

    def get_q2(do_model=None, search_str=None, q_field_pre=None, q_field_lookup='', r_depth=None):
        text_fields = []
        char_fields = []
        date_fields = []
        other_fields = []
        one2one_fields = []
        many2many_fields = []
        foreign_fields = []
        queries = []
        one2onerel_fields = []
        many2manyrel_fields = []
        many2onerel_fields = []

        # print('r_depth: %s' % r_depth)
        if r_depth is not None and r_depth > r_depth_max:
            return []

        for f in get_model_all_files(do_model):
            if isinstance(f, CharField):
                char_fields.append(f)
            elif isinstance(f, OneToOneField):
                one2one_fields.append(f)
            elif isinstance(f, ManyToManyField):
                many2many_fields.append(f)
            elif isinstance(f, ForeignKey):
                foreign_fields.append(f)
            elif isinstance(f, DateTimeField) or isinstance(f, DateField) or isinstance(f, TimeField):
                date_fields.append(f)
            elif isinstance(f, TextField):
                text_fields.append(f)
            elif isinstance(f, OneToOneRel):
                one2onerel_fields.append(f)
            elif isinstance(f, ManyToManyRel):
                many2manyrel_fields.append(f)
            elif isinstance(f, ManyToOneRel):
                many2onerel_fields.append(f)
            else:
                other_fields.append(f)

        #
        # if is_contain_chinese(search_str):  # mysql的搜索时间字段不能使用中文关键词
        #     do_search_files = char_fields + text_fields
        # else:
        #     do_search_files = char_fields + text_fields

        do_search_files = char_fields + text_fields + other_fields

        for cf in do_search_files:
            if cf.name in black_fields:
                continue
            if q_field_pre is not None:
                queries.append(Q(**{'%s__%s__%s' % (q_field_pre, cf.name, q_field_lookup): search_str}))
            else:
                queries.append(Q(**{'%s__%s' % (cf.name, q_field_lookup): search_str}))

        # do_r_fields = one2onerel_fields + one2one_fields + foreign_fields + many2many_fields + many2onerel_fields + many2manyrel_fields
        do_r_fields = foreign_fields + one2one_fields + one2onerel_fields

        # do_r_fields = one2one_fields + foreign_fields
        for rf in do_r_fields:

            r_model = rf.related_model
            if r_model._meta.model_name in black_models:
                continue

            if r_model == do_model or r_model == s_model:
                continue
            if r_model in done_models:
                continue
            done_models.append(r_model)
            if q_field_pre is not None:
                n_q_field_pre = '%s__%s' % (q_field_pre, rf.name)
            else:
                n_q_field_pre = rf.name
            if r_depth is None:
                do_r_depth = 1
            else:
                do_r_depth = copy.copy(r_depth) + 1
            queries = queries + get_q2(do_model=r_model, search_str=search_str, q_field_pre=n_q_field_pre,
                                       q_field_lookup=q_field_lookup, r_depth=do_r_depth)

        return queries

    qs = Q()
    if isinstance(s_q2, list) and len(s_q2) > 0:
        q2 = s_q2
    else:
        if len(q_fields) > 0:
            queries = []
            for qf in q_fields:
                queries.append(Q(**{'%s__%s' % (qf, q_field_lookup): s_str}))
            q2 = queries
        else:
            q2 = get_q2(do_model=d_model, search_str=s_str, q_field_lookup=q_field_lookup)
    # for q in q2:
    #     print(q)
    q2 = sorted(q2, key=lambda y: len(y.__str__().split('__')), reverse=False)  # 按广度优先排序搜索语句
    q2 = q2[:61]  # mysql最多只支持一次61个表联合查询
    # print('----------')
    # for q in q2:
    #     print(q)
    qs = reduce(operator.or_, q2)
    return qs


def filter_query(model_object, search_str, order_by_str):
    if order_by_str is None or order_by_str == '':
        order_by_str = 'id'
    s_black_fields = ['id']
    s_black_models = ['userprofile', 'eventlog', ]
    s_r_depth_max = 5
    s_limit = {'black_fields': s_black_fields, 'black_models': s_black_models, 'r_depth_max': s_r_depth_max}
    q_filed_lookup = 'icontains'
    if hasattr(model_object, 's_fields'):
        search_f = model_object.s_fields()
    else:
        search_f = []

    if hasattr(model_object, 'q_fields'):
        q_fields = model_object.q_fields()
    else:
        q_fields = []
    search_i = {'limit': s_limit, 'q_field_lookup': q_filed_lookup,
                'q_fields': q_fields}
    qs = get_qs(model_object, search_str, search_i=search_i)
    q_data = model_object.objects.order_by(order_by_str).filter(qs)

    return q_data


def save_model_data(model_cls, **kwargs):
    '''
    自动保存Form对象数据至Model
    :param model:
    :param kwargs:
    :return:
    '''
    m2m_fields = model_cls._meta.many_to_many
    m2m_data = {}
    for m2m in m2m_fields:
        if m2m.name in kwargs:
            m2m_data[m2m.name] = kwargs[m2m.name]
            del kwargs[m2m.name]

    fk_lists = []
    for field in model_cls._meta.fields:
        if hasattr(field, 'related'):
            fk_lists.append(field)

    id = kwargs.get('id', None)
    if id:
        now = model_cls.objects.get(pk=id)
        for fk in fk_lists:
            fk_object = getattr(now, fk.name)
            if hasattr(fk_object, 'status'):
                fk_object.status = 1
                fk_object.save()

    new_instance = model_cls(**kwargs)
    new_instance.save()

    for fk in fk_lists:
        fk_object = getattr(new_instance, fk.name)
        if hasattr(fk_object, 'status'):
            fk_object.status = 0
            fk_object.save()

    if m2m_data:
        for field in m2m_fields:
            if not field.remote_field.related_name:
                model_rel_field = field.related_query_name()  # 获取model查询名称（一般是类名的小写）
                had_relates = []  # 数据库中原有已选中元素
                '''
                获取对象原来绑定的所有m2m元素
                '''
                f_dict = {model_rel_field: new_instance}
                tmp_relates = []
                had_relates = [x for x in field.remote_field.through.objects.filter(**f_dict)]  # 获取数据库中原有已选中元素
                m2m_data_field_d = m2m_data[field.name]  # 获取field名称
                m2m_data_filed_r_modle_name = field.remote_field.model._meta.model_name  # 获取m2m的model类的名称（一般是类名的小写）
                m2m_data_filed_r_modle = field.remote_field.model  # 获取 m2m的 model类

                if m2m_data_field_d is None:
                    continue

                for data in m2m_data_field_d:
                    f_dict[m2m_data_filed_r_modle_name] = data
                    '''
                    首先尝试插入选中的元素，如果出错，则判断该元素已存在。
                    '''
                    try:
                        rel_through_ins = None
                        rel_through_ins = field.remote_field.through.objects.create(**f_dict)
                        if rel_through_ins is not None:
                            rel_through_ins.save()
                        if hasattr(data, 'status'):
                            data.status = 0  # 这里实现的逻辑是，如果已被使用，标记该m2m元素状态为已用，下回过滤掉此状态的元素，一般用在某些元素只能为单个对象所拥有的场景
                            data.save()
                        # 保存已选中的所有元素
                        tmp_relates.append(rel_through_ins)
                    except IntegrityError as e:
                        x = []
                        x = field.remote_field.through.objects.filter(**f_dict)
                        # 保存已选中的所有元素
                        tmp_relates += [r for r in x]
                now_relates = tmp_relates

                del_relates = []  # 待删除元素集合

                if isinstance(had_relates, list) and isinstance(now_relates, list):
                    del_relates = list(set(had_relates).difference(set(now_relates)))

                for rel in del_relates:
                    m2m_object = getattr(rel, m2m_data_filed_r_modle_name)
                    # print m2m_object
                    if hasattr(m2m_object, 'status'):
                        m2m_object.status = 1  # 如果删除了m2m绑定，同时把元素的状态恢复。
                    rel.delete()
            else:
                n_relate_moel = getattr(new_instance, field.name)
                # 这里需要斟酌下！,需考虑目标model是否有status字段
                if n_relate_moel is not None and hasattr(n_relate_moel, 'status'):
                    # if n_relate_moel is not None:
                    n_relate_moel.update(status=1)
                datas = m2m_data[field.name]
                if datas is None:
                    continue
                for data in datas:
                    # print hasattr(data,'status')
                    if hasattr(data, 'status'):
                        data.status = 0
                        data.save()
                if hasattr(new_instance, field.name) and hasattr(getattr(new_instance, field.name), 'set'):
                    getattr(getattr(new_instance, field.name), 'set')(m2m_data[field.name])
                else:
                    setattr(new_instance, field.name, m2m_data[field.name])

    return new_instance


def del_model_data(model, **kwargs):
    id = kwargs.get('id', None)
    instance = get_object_or_404(model, pk=id)

    if instance:
        fk_lists = []
        for field in model._meta.fields:
            if hasattr(field, 'related'):
                fk_lists.append(field)

        for fk in fk_lists:
            fk_object = getattr(instance, fk.name)
            if hasattr(fk_object, 'status'):
                fk_object.status = 1
                # print "Change status FK:",fk_object,", Status ",fk_object.status,"\n"
                fk_object.save()

        m2m_fields = model._meta.many_to_many

        for m2m_field in m2m_fields:
            m2m_datas = getattr(instance, m2m_field.name)
            for m2m_object in m2m_datas.get_queryset():
                if hasattr(m2m_object, 'status'):
                    m2m_object.status = 1
                    # print "Change status M2M:",m2m_object,", Status ",m2m_object.status
                    m2m_object.save()
                try:
                    m2m_datas.remove(m2m_object)
                except(AttributeError, e):
                    f_dict = {m2m_datas.target_field.name: m2m_object}
                    m2m_datas.through.objects.get(**f_dict).delete()

        code = 0
        msg = 'Delete Success !'
        instance.delete()
        # print "Instance Delete"
    else:
        code = 1
        msg = 'Delete Failed !'

    del_res = {
        'code': code,
        'msg': msg
    }
    return del_res
