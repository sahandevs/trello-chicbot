from trello import List, Card


def copy_card(card: Card, to_list: List, labels, assign):
  labels_str = ""
  if labels:
    for label in labels:
      labels_str += label + ","

  members_str = ""
  if assign:
    for assignee in assign:
      members_str += assignee + ","

  post_args = {
    'name': card.name,
    'idList': to_list.id,
    'desc': card.desc,
    'idLabels': labels_str[:-1],
    'due': card.due,
    'idMembers': members_str[:-1],
    'idCardSource': card.id,
    'keepFromSource': 'attachments,checklists,comments,stickers'
  }

  created_card = to_list.client.fetch_json(
    '/cards',
    http_method='POST',
    post_args=post_args)
  return Card.from_json(to_list, created_card)
