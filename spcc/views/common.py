# coding=utf-8


import json

from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.core.paginator import Paginator, InvalidPage, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from spmo.common import Common
from spmo.data_serialize import DataSerialize
from spcc.models.common import get_qs, split_model_field, get_model_fields

co = Common()


def list_data(**kwargs):
    each_page_items = int(kwargs.get('each_page_items', 10))
    show_field_list = kwargs.get('show_field_list', [])
    show_fieldvname_dict = kwargs.get('show_fieldvname_dict', {})
    ex_field_list = kwargs.get('ex_field_list', [])
    request = kwargs.get('request', {})
    page_nav_base_url = kwargs.get('page_nav_base_url', '')
    show_error_url = kwargs.get('show_error_url', '/')
    show_list_uri = kwargs.get('show_list_uri', [])
    nav_uri = kwargs.get('nav_uri', [])
    custom_get_parameter = kwargs.get('custom_get_parameter', {})
    filter_field = kwargs.get('filter_field', 'id')
    template_file = kwargs.get('template_file', '')
    model_object = kwargs.get('model_object', '')
    is_frontend_paging = kwargs.get('is_frontend_paging', False)
    return_type = kwargs.get('return_type', 'render_to_response')
    search_i = kwargs.get('search_i', {})
    filter_class = kwargs.get('filter_class', None)
    app = kwargs.get('app', {})

    # show_field_list = get_model_all_field_objects(model=model_object)

    after_range_num = 5
    bevor_range_num = 4
    page = 1
    sort_by = ''
    url_prefix_base = ''
    url_sort_prefix = ''
    url_prefix = '?page='
    query = ''
    filter_action = 'false'
    # if is_frontend_paging:
    #     info = model_object.objects.all()
    #     item_list = [info]
    if is_frontend_paging:
        each_page_items = 100000

    if len(custom_get_parameter) < 1 and request.method == 'GET':
        try:
            page = int(request.GET.get("page", 1))
            query = request.GET.get('q', '')
            sort_by = request.GET.get('sort_by', '')
            filter_action = request.GET.get('filter_action', 'false')

            if page < 1:
                page = 1
        except ValueError:
            page = 1
    else:
        query = custom_get_parameter.get('query', [])
        sort_by = custom_get_parameter.get('sort_by', 'id')
        page = custom_get_parameter.get('page', 1)
        if page < 1:
            page = 1
    sorted_by = sort_by
    if sort_by is not None and sort_by != '':
        url_sort_prefix = '?sort_by='
        url_prefix = "?page="
    else:
        sort_by = '-id'
        url_prefix_base = "?sort_by=%s" % sort_by
        url_sort_prefix = "?sort_by="
        url_prefix = url_prefix_base + "&page="

    if filter_action == 'true':
        r_get = request.GET.dict()
        del r_get['filter_action']
        info = filter_class(r_get, queryset=model_object.objects.all()).qs
    elif (query is not None and query != ''):
        if sorted_by is None or sorted_by == '':
            url_prefix_base = "?q=%s" % query
            url_sort_prefix = url_prefix_base + '&sort_by='
            url_prefix = url_prefix_base + '&page='
        else:
            url_prefix_base = "?q=%s" % query
            url_sort_prefix = url_prefix_base + '&sort_by='
            url_prefix = url_prefix_base + "&sort_by=%s&page=" % sort_by

        # info = model_object.objects.order_by(sort_by).filter(eval("Q(%s__contains=\"%s\")" % (filter_field, query)))
        qs = get_qs(model_object, query, search_i=search_i)
        info = model_object.objects.order_by(sort_by).filter(qs)
    else:

        if sorted_by is None or sorted_by == '':
            url_sort_prefix = '?sort_by='
            url_prefix = '?page='
        else:
            url_sort_prefix = '?sort_by='
            url_prefix = "?sort_by=%s&page=" % sort_by
        info = model_object.objects.order_by(sort_by).all()

    '''
    获取字段的verbose_name
    '''
    for fieldname in show_field_list:
        m_field = model_object._meta.get_field(fieldname)
        if hasattr(m_field, 'verbose_name'):
            show_fieldvname_dict[fieldname] = getattr(m_field, 'verbose_name')
        else:
            show_fieldvname_dict[fieldname] = getattr(m_field, 'name')

    paginator = Paginator(info, each_page_items)
    try:
        item_list = paginator.page(page)
    except(EmptyPage, InvalidPage, PageNotAnInteger):
        item_list = paginator.page(1)
    page_range_l = list(paginator.page_range)
    if page >= after_range_num:
        page_range = page_range_l[page - after_range_num:page + bevor_range_num]
    else:
        page_range = page_range_l[0:int(page) + bevor_range_num]

    """可以返回三种类型数据： 
       1、 render_to_response 返回一个 Http Response 有http头部（比如Content-Type: xxx xxx)
       2、 render_to_string  只是返回内容的字符串形式，没有http头部（Content-Type: xxx xxx）
       3、 var     则只是返回 内容的变量（比如 locals）
    """

    if return_type == 'render_to_response':
        return render(request, template_file, locals(), )
    elif return_type == 'render_to_string':
        return render_to_string(template_file, locals())
    elif return_type == 'var':
        return locals()


def list_data_for_ajax_with_datatable(**kwargs):
    show_field_list = kwargs.get('show_field_list', [])
    request = kwargs.get('request', {})
    model_object = kwargs.get('model_object', '')
    m_fields_name = kwargs.get('m_fields_name', [])
    # search_i = kwargs.get('search_i', {})
    filter_class = kwargs.get('filter_class', None)
    data_table = {}
    aodata = json.loads(request.POST.get("aodata"))
    filter_parm_str = request.POST.get("filter_parm")
    filter_action = request.POST.get("filter_action")
    if filter_parm_str is not None and filter_parm_str != '':
        filter_parm = json.loads(filter_parm_str)
    else:
        filter_parm = {}

    # parse datatable parm.
    c_info = {}
    g_info = {}
    s_info = {}
    it_word = ['mDataProp', 'sSearch', 'bRegex', 'bSearchable', 'bSortable']
    sort_word = ['iSortCol', 'sSortDir']
    for item in aodata:
        i_match = False
        s_match = False
        # print('key=%s, val=%s' % (item['name'], item['value']))
        for it_w in it_word:
            it_w_v = it_w + '_'
            if item['name'].startswith(it_w_v):
                it_w_s = item['name'].split('_')
                if len(it_w_s) == 2:
                    i_match = True
                    if it_w_s[-1] not in c_info:
                        c_info[it_w_s[-1]] = {}
                    c_info[it_w_s[-1]][it_w] = item['value']

        for st_w in sort_word:
            st_w_v = st_w + '_'
            if item['name'].startswith(st_w_v):
                st_w_s = item['name'].split('_')
                if len(st_w_s) == 2:
                    s_match = True
                    if st_w_s[-1] not in s_info:
                        s_info[st_w_s[-1]] = {}
                    s_info[st_w_s[-1]][st_w] = item['value']

        if i_match is False and s_match is False:
            g_info[item['name']] = item['value']

    s_echo = int(g_info.get('sEcho', 1))  # 客户端发送的标识
    i_display_start = int(g_info.get('iDisplayStart', 2))  # 起始索引
    i_display_length = int(g_info.get('iDisplayLength', 10))  # 每页显示的行数
    search_str = g_info.get('sSearch', '').lstrip(' ').rstrip(' ')  # 搜索关键字

    order_by_str = 'id'
    o_field = 'id'
    o_field_dir = 'asc'
    if len(s_info) > 0:
        order_d = s_info.pop('0')
        o_field = c_info[str(order_d['iSortCol'])]['mDataProp']
        o_field_dir = order_d['sSortDir'].lower()
        if o_field in m_fields_name:
            if o_field_dir == 'asc':
                order_by_str = o_field
            else:
                order_by_str = '-' + o_field

    if filter_action == 'true' and isinstance(filter_parm, dict):
        q_data = filter_class(filter_parm, queryset=model_object.objects.order_by(order_by_str).all()).qs
    elif search_str is not None and search_str != '':
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

    else:
        q_data = model_object.objects.order_by(order_by_str).all()

    result_length = q_data.count()

    if i_display_length == -1:  # 显示全部
        i_display_length = result_length

    # 对list进行分页
    paginator = Paginator(q_data, i_display_length)
    try:
        q_data = paginator.page(i_display_start / i_display_length + 1)
    # 请求页数错误
    except PageNotAnInteger:
        q_data = paginator.page(1)
    except EmptyPage:
        q_data = paginator.page(paginator.num_pages)
    data = []
    for item in q_data:
        data.append(item.visualize())
    # 如果排序字段不属于当前model,（这里有bug，只会对当前页进行排序）
    if o_field not in m_fields_name:
        # print('o_field: %s, o_field_dir: %s' % (o_field, o_field_dir))
        if o_field_dir == 'asc':
            data = sorted(data, key=lambda item: item[o_field])
        else:
            data = sorted(data, key=lambda item: item[o_field], reverse=True)
    # print('o_field: %s, o_field_dir: %s' % (o_field, o_field_dir))
    # co.DD(s_info)
    # co.DD(c_info)

    data_table['iTotalRecords'] = result_length  # 数据总条数
    data_table['sEcho'] = s_echo + 1
    data_table['iTotalDisplayRecords'] = result_length  # 显示的条数
    data_table['aaData'] = data
    # co.DD(data_table)

    return HttpResponse(json.dumps(data_table, ensure_ascii=False))


def del_model_items(*args, **kwargs):
    del_model = kwargs.get('del_model', None)
    del_items = kwargs.get('del_items', None)
    if del_items.find(',') != -1:
        mult_ids = []
        mult_ids = del_items.split(',')
        if mult_ids[0] == 'undefined':
            return False
        for p_id in mult_ids:
            del_model_instance = get_object_or_404(del_model, pk=p_id)
            if del_model_instance:
                del_model_instance.delete()
    else:
        del_model_instance = get_object_or_404(del_model, pk=del_items)
        if del_model_instance:
            del_model_instance.delete()


def display_confirm_msg(*args, **kwargs):
    request = kwargs.get('request', None)
    http_referer = kwargs.get('http_referer', None)
    confirm_back_url = kwargs.get('confirm_back_url', http_referer)
    confirm_msg = kwargs.get('confirm_msg', None)
    confirm_title = kwargs.get('confirm_title', None)
    # confirm_next_url = kwargs.get('confirm_next_url', "%s?confirm_result=yes&s_url=%s" % (request.path, http_referer) )
    confirm_next_url = kwargs.get('confirm_next_url', "%s?confirm_result=yes" % (request.path))
    confirm_back_title = kwargs.get('confirm_back_title', 'Back')
    # logger2.info( "%s, %s, %s, %s, %s, %s" % (http_referer, confirm_back_url, confirm_msg, confirm_title, confirm_next_url, confirm_back_title) )
    return render(request, 'confirm_action.html',
                  {'confirm_msg': confirm_msg, 'confirm_title': confirm_title, 'confirm_next_url': confirm_next_url,
                   'confirm_back_title': confirm_back_title, 'confirm_back_url': confirm_back_url}, )


def map_value(value="", map_list=()):
    res = ''
    for x in map_list:
        try:
            value = int(value)
        except(ValueError):
            value = value
        if x[0] == value:
            res = x[1]
    if not res:
        res = "none"
    return res


class Ajax(Common):
    def __init__(self, *args, **kwargs):
        self.s_method = kwargs.get('s_method', ['GET', 'POST'])
        self.request = kwargs.get('request', None)
        self.original_data = kwargs.get('original_data', 'form')
        self.is_origin_serial = kwargs.get('is_origin_serial', False)
        ds = kwargs.get('ds', None)
        if isinstance(ds, DataSerialize):
            self.ds = ds
        else:
            self.ds = DataSerialize(format='json', ensure_ascii=False)

        self.error_m = {'error_code': -1, 'error_msg': 'Only support %s method!' % (','.join(self.s_method)), }
        self.response = HttpResponse('')
        self.response['Content-Type'] = "application/json; charset=utf-8"
        self.response['Vary'] = "Accept-Language"
        self.response_content = None

        self.callback(self, *args, **kwargs)

    def callback(self, *args, **kwargs):
        pass

    def load_data(self, content=None):
        self.response_content = content

    def get_ds_input_data(self):
        if self.request.method == 'POST':
            if self.original_data == 'form':
                self.in_data = self.request.POST
            else:
                self.in_data = self.request.body
        elif self.request.method == 'GET':
            self.in_data = self.request.GET
        else:
            self.in_data = {}
        # if self.is_origin_serial: #这里会产生错误。
        #   self.in_data=self.ds.deserialize('{"cc":1}')
        return self.in_data

    def make_response(self, *args, **kwargs):
        if self.request.method in self.s_method:
            self.response.content = self.ds.serialize(self.response_content)
        else:
            self.response.content = self.ds.serialize(self.error_m)
        return self.response
