import requests
import json

def http_request(uri: str, method: str, headers: dict = {},
                 body: dict = {}, params: dict = {}, files: dict | None = None, is_pcap: bool = False, is_xml: bool = False) -> Any:
    """
    Makes an API call with the given arguments
    """
    result = requests.request(
        method,
        uri,
        headers=headers,
        data=body,
        verify=False,
        params=params,
        files=files
    )

    if result.status_code < 200 or result.status_code >= 300:
        raise Exception(
            'Request Failed. with status: ' + str(result.status_code) + '. Reason is: ' + str(result.reason))

    # if pcap download
    if is_pcap:
        return result
    if is_xml:
        return result.text

    json_result = json.loads(xml2json(result.text))

    # handle raw response that does not contain the response key, e.g configuration export
    if ('response' not in json_result or '@code' not in json_result['response']) and \
            not json_result['response']['@status'] != 'success':
        return json_result

    # handle non success
    if json_result['response']['@status'] != 'success':
        if 'msg' in json_result['response'] and 'line' in json_result['response']['msg']:
            response_msg = json_result['response']['msg']['line']
            # catch non existing object error and display a meaningful message
            if response_msg == 'No such node':
                raise Exception(
                    'Object was not found, verify that the name is correct and that the instance was committed.')

            #  catch urlfiltering error and display a meaningful message
            elif str(response_msg).find('test -> url') != -1:
                if DEVICE_GROUP:
                    raise Exception('URL filtering commands are only available on Firewall devices.')
                if 'Node can be at most 1278 characters' in response_msg:
                    raise InvalidUrlLengthException('URL Node can be at most 1278 characters.')
                raise Exception('The URL filtering license is either expired or not active.'
                                ' Please contact your PAN-OS representative.')

            # catch non valid jobID errors and display a meaningful message
            elif isinstance(json_result['response']['msg']['line'], str) and \
                    json_result['response']['msg']['line'].find('job') != -1 and \
                    (json_result['response']['msg']['line'].find('not found') != -1
                     or json_result['response']['msg']['line'].find('No such query job')) != -1:
                raise Exception('Invalid Job ID error: ' + json_result['response']['msg']['line'])

            # catch already at the top/bottom error for rules and return this as an entry.note
            elif str(json_result['response']['msg']['line']).find('already at the') != -1:
                return_results('Rule ' + str(json_result['response']['msg']['line']))
                sys.exit(0)

            # catch already registered ip tags and return this as an entry.note
            elif str(json_result['response']['msg']['line']).find('already exists, ignore') != -1:
                if isinstance(json_result['response']['msg']['line']['uid-response']['payload']['register']['entry'],
                              list):
                    ips = [o['@ip'] for o in
                           json_result['response']['msg']['line']['uid-response']['payload']['register']['entry']]
                else:
                    ips = json_result['response']['msg']['line']['uid-response']['payload']['register']['entry']['@ip']
                return_results(
                    'IP ' + str(ips) + ' already exist in the tag. All submitted IPs were not registered to the tag.')
                sys.exit(0)

            # catch timed out log queries and return this as an entry.note
            elif str(json_result['response']['msg']['line']).find('Query timed out') != -1:
                return_results(str(json_result['response']['msg']['line']) + '. Rerun the query.')
                sys.exit(0)

        if '@code' in json_result['response']:
            raise Exception(
                'Request Failed.\nStatus code: ' + str(json_result['response']['@code']) + '\nWith message: ' + str(
                    json_result['response']['msg']['line']))
        else:
            raise Exception('Request Failed.\n' + str(json_result['response']))

    # handle @code
    if json_result['response']['@code'] in PAN_OS_ERROR_DICT:
        error_message = 'Request Failed.\n' + PAN_OS_ERROR_DICT[json_result['response']['@code']]
        if json_result['response']['@code'] == '7' and DEVICE_GROUP:
            device_group_names = get_device_groups_names()
            if DEVICE_GROUP not in device_group_names:
                error_message += (f'\nDevice Group: {DEVICE_GROUP} does not exist.'
                                  f' The available Device Groups for this instance:'
                                  f' {", ".join(device_group_names)}.')
            xpath = params.get('xpath') or body.get('xpath')
            demisto.debug(f'Object with {xpath=} was not found')
            raise PAN_OS_Not_Found(error_message)
        return_warning('List not found and might be empty', True)
    if json_result['response']['@code'] not in ['19', '20']:
        # error code non exist in dict and not of success
        if 'msg' in json_result['response']:
            raise Exception(
                'Request Failed.\nStatus code: ' + str(json_result['response']['@code']) + '\nWith message: ' + str(
                    json_result['response']['msg']))
        else:
            raise Exception('Request Failed.\n' + str(json_result['response']))

    return json_result

def build_logs_query(address_src: Optional[str], address_dst: Optional[str], ip_: Optional[str],
                     zone_src: Optional[str], zone_dst: Optional[str], time_generated: Optional[str],
                     action: Optional[str], port_dst: Optional[str], rule: Optional[str], url: Optional[str],
                     filedigest: Optional[str]):
    query = ''
    if address_src:
        query += build_array_query(query, address_src, 'addr.src', 'in')
    if address_dst:
        if len(query) > 0 and query[-1] == ')':
            query += ' and '
        query += build_array_query(query, address_dst, 'addr.dst', 'in')
    if ip_:
        if len(query) > 0 and query[-1] == ')':
            query += ' and '
        query = build_array_query(query, ip_, 'addr.src', 'in')
        query += ' or '
        query = build_array_query(query, ip_, 'addr.dst', 'in')
    if zone_src:
        if len(query) > 0 and query[-1] == ')':
            query += ' and '
        query += build_array_query(query, zone_src, 'zone.src', 'eq')
    if zone_dst:
        if len(query) > 0 and query[-1] == ')':
            query += ' and '
        query += build_array_query(query, zone_dst, 'zone.dst', 'eq')
    if port_dst:
        if len(query) > 0 and query[-1] == ')':
            query += ' and '
        query += build_array_query(query, port_dst, 'port.dst', 'eq')
    if time_generated:
        if len(query) > 0 and query[-1] == ')':
            query += ' and '
        query += '(time_generated leq ' + time_generated + ')'
    if action:
        if len(query) > 0 and query[-1] == ')':
            query += ' and '
        query += build_array_query(query, action, 'action', 'eq')
    if rule:
        if len(query) > 0 and query[-1] == ')':
            query += ' and '
        query += build_array_query(query, rule, 'rule', 'eq')
    if url:
        if len(query) > 0 and query[-1] == ')':
            query += ' and '
        query += build_array_query(query, url, 'url', 'contains')
    if filedigest:
        if len(query) > 0 and query[-1] == ')':
            query += ' and '
        query += build_array_query(query, filedigest, 'filedigest', 'eq')

    return query

def panorama_query_logs(log_type: str, number_of_logs: str, query: str, address_src: str, address_dst: str, ip_: str,
                        zone_src: str, zone_dst: str, time_generated: str, action: str,
                        port_dst: str, rule: str, url: str, filedigest: str):
    params = {
        'type': 'log',
        'log-type': log_type,
        'key': API_KEY
    }

    if filedigest and log_type != 'wildfire':
        raise Exception('The filedigest argument is only relevant to wildfire log type.')
    if url and log_type == 'traffic':
        raise Exception('The url argument is not relevant to traffic log type.')

    if query:
        params['query'] = query
    else:
        if ip_ and (address_src or address_dst):
            raise Exception(
                'The ip argument cannot be used with the address-source or the address-destination arguments.')
        params['query'] = build_logs_query(address_src, address_dst, ip_,
                                           zone_src, zone_dst, time_generated, action,
                                           port_dst, rule, url, filedigest)
    if number_of_logs:
        params['nlogs'] = number_of_logs

    result = http_request(
        URL,
        'GET',
        params=params,
    )

    return result

