# coding=utf-8

from django import template

from spcc.views.common import map_value

from django.conf import settings

register = template.Library()


def get_model_all_fields(model=None):
    '''
    获取model所有field，包括外键，多对多等
    :param model:
    :return:
    '''
    return list(set([f for f in model._meta.get_fields() if f.many_to_one or f.many_to_many or f.concrete]))


def do_filed_data_analysis(parser, token):
    try:
        tag_name, object_data, object_show_fields, object_ex_fields = token.split_contents()
    except:
        raise (template.TemplateSyntaxError, "%r tags error" % token.split_contents()[0])

    return FieldDataNode(object_data, object_show_fields, object_ex_fields)


class FieldDataNode(template.Node):
    def __init__(self, object_data, object_show_fields, object_ex_fields):
        self.object = template.Variable(object_data)
        self.show_fields = template.Variable(object_show_fields)
        self.ex_fields = template.Variable(object_ex_fields)

    def reset_host_num(self, data):
        data.sort()
        result = []
        flag = 0
        num_start = 0
        for num in range(len(data)):
            if num == len(data) - 1:
                if flag == 1:
                    num_end = data[num]
                    result.append(str(num_start) + ".." + str(num_end))
                else:
                    result.append(str(data[num]))
                break
            if data[num + 1] - data[num] != 1:
                if flag == 0:
                    result.append(str(data[num]))
                if flag == 1:
                    num_end = data[num]
                    result.append(str(num_start) + ".." + str(num_end))
                flag = 0
            elif data[num + 1] - data[num] == 1:
                if flag == 0:
                    num_start = data[num]
                flag = 1
        return result

    def reset_host_name(self, data):
        result = []
        data_dict = dict()
        for item in data:
            postfix = '.'.join(item.split(".")[1:])
            prefix = item.split(".")[0]
            type = prefix[:2]
            ip = prefix[2:]
            if postfix not in data_dict.keys():
                data_dict[postfix] = {type: [int(ip)]}
                continue

            if type not in data_dict[postfix].keys():
                data_dict[postfix][type] = [int(ip)]
            else:
                data_dict[postfix][type].append(int(ip))

        for x, y in data_dict.items():
            for i, j in y.items():
                result_num = self.reset_host_num(j)
                for num in result_num:
                    result.append(i + num + "." + x)
        return result

    def render(self, context):
        object = self.object.resolve(context)
        show_fields = self.show_fields.resolve(context)
        ex_fields = self.ex_fields.resolve(context)
        model = type(object)
        model_m2m_fs = model._meta.many_to_many

        data = {}
        f_keys = []
        items = {}
        if hasattr(object, 'items'):
            items = object.items()
        else:
            items = [(field, field.value_to_string(object)) for field in object._meta.fields]
        # print 'items: %s' % items
        for field, value in items:
            data[field.name] = "none"
            if hasattr(field, 'choices') and len(field.choices) > 0:
                data[field.name] = getattr(object, 'get_%s_display' % field.name)()
            else:
                if hasattr(field, 'related_fields'):
                    data[field.name] = getattr(object, field.name)
                    f_keys.append(field.name)
                else:
                    data[field.name] = value

        # for m2m_field in model_m2m_fs:
        #     m2m_datas=getattr(object,'%s' % m2m_field.name).all()
        #     for m2m in m2m_datas:
        #         data[m2m_field.name].append(m2m.__unicode__())
        #     data[m2m_field.name]=",".join(data[m2m_field.name])

        ex_data = {}
        res_str = ""
        for ex_key in ex_fields:
            if not ex_key in ex_data:
                ex_data[ex_key] = {}
            if ex_key == "m2m":
                for x, y in ex_fields[ex_key]['fields'].items():
                    m2m_datas = getattr(object, '%s' % x).all()
                    ex_data_tmp = []
                    for m2m in m2m_datas:
                        ex_data_tmp.append(getattr(m2m, "%s" % y))
                    if y == "host_name":
                        ex_data_tmp = self.reset_host_name(ex_data_tmp)
                    ex_data[ex_key].update({x: ",".join(ex_data_tmp[:])})
                for ex_key in ex_data:
                    for fl in ex_fields[ex_key]['fields'].keys():
                        res_str = u"%s<td>%s</td>" % (res_str, ex_data[ex_key][fl])
            elif "m2m" == ex_key.split("_")[-1]:
                ex_key_va = "_".join(ex_key.split("_")[:-1])
                ex_model = eval('%s' % ex_key_va)
                for field_name, m2m_field in ex_fields[ex_key]["fields"].items():
                    relation_name = getattr(ex_model.objects.all()[0], '%s' % m2m_field).query_field_name
                    m2m_datas = getattr(object, '%s' % relation_name).all()
                    ex_data_tmp = []
                    for m2m in m2m_datas:
                        ex_data_tmp.append(getattr(m2m, "%s" % field_name))
                    ex_data[ex_key].update({field_name: ",".join(ex_data_tmp[:])})
                for ex_key in ex_data:
                    for fl in ex_fields[ex_key]['fields'].keys():
                        res_str = u"%s<td>%s</td>" % (res_str, ex_data[ex_key][fl])
            else:
                ex_model = eval('%s' % ex_key)
                ex_filter = ex_fields[ex_key]['filter']
                f_words = []
                for ft in ex_filter:
                    for k in ex_filter[ft]:
                        if ft == 'st':
                            f_words.append('%s=%s' % (k, ex_filter[ft][k]))
                        elif ft == 'dy':
                            f_words.append('%s=object.%s' % (k, ex_filter[ft][k]))
                exec("ex_qset=ex_model.objects.filter(%s)" % ','.join(f_words))

                for fl in ex_fields[ex_key]['fields']:
                    if not ex_key in ex_data:
                        ex_data[ex_key] = {}
                    if ex_qset:
                        ex_data[ex_key].update({fl: getattr(ex_qset[0], fl)})
                    else:
                        ex_data[ex_key].update({fl: "None"})

                for ex_key in ex_data:
                    for fl in ex_fields[ex_key]['fields']:
                        res_str = u"%s<td>%s</td>" % (res_str, ex_data[ex_key][fl])

        for key in show_fields:
            if key in data:
                # print "K:%s,V:%s" % (key,data[key])
                field_o = getattr(object, key)
                if key in f_keys and hasattr(field_o, 'get_absolute_url'):
                    res_str = u"%s<td><a href=%s >%s</a></td>" % (res_str, field_o.get_absolute_url(), data[key])
                else:
                    res_str = u"%s<td>%s</td>" % (res_str, data[key])
            else:
                res_str = u"%s<td>%s</td>" % (res_str, "None")

        return res_str


register.tag('field_data', do_filed_data_analysis)
