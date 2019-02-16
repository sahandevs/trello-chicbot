from trello import TrelloClient, Board, Card, Label
import trello
from typing import *
import sys
import json5
from lib_trello.trello_extensions import copy_card


class Bot:
  config: dict

  client: TrelloClient

  source_board: Board
  dest_board: Board

  list_mapping: Dict[trello.List, trello.List]
  label_to_list_mapping: Dict[str, trello.List]
  label_mapping: Dict[Label, List[Label]]

  member_via_label: Dict[str, List[str]]
  comment_via_label: Dict[str, List[str]]

  comment_from_list: Dict[str, List[str]]

  need_confirmation: bool

  copy_from_source: bool

  def __init__(self, config: dict):
    self.config = config
    self.need_confirmation = config.get('need_confirmation', False)
    self.copy_from_source = config.get('copy_from_source', False)

  def start(self):
    # create client
    print("logging in...")
    self.client = TrelloClient(api_key=self.config['api_key'], api_secret=self.config['api_secret'])
    # get boards
    print("finding boards...")
    for board in self.client.list_boards():
      if self.config['source_board'] in board.name:
        self.source_board = board
      elif self.config['destination_board'] in board.name:
        self.dest_board = board

    # check config if extract info extract else start bot
    if self.config.get('extract_board_info', False):
      self.extract_info()
    else:
      self.start_bot()

  @staticmethod
  def extract_board_info(board: Board):
    print('== Members')
    for member in board.all_members():
      print('{0}({1}) : {2}'.format(member.full_name, member.username, member.id))
    print('== Labels')
    for label in board.get_labels():
      print('[{0}]{1} : {2}'.format(label.color, label.name, label.id))
    print('== Lists')
    for list in board.list_lists():
      print('{0} : {1}'.format(list.name, list.id))

  def extract_info(self):
    print('extracting info...')
    print('\n\n=============== Source Board: {0}'.format(self.source_board.name))
    Bot.extract_board_info(self.source_board)
    print('\n\n=============== Destination Board: {0}'.format(self.dest_board.name))
    Bot.extract_board_info(self.dest_board)

  # bot

  def prepare_label_to_list_mapping(self):
    print('preparing label to list mappings...')
    list_mapping = self.config.get('label_to_list_mapping', {})
    from_map_labels: List[str] = []
    to_map_list: List[trello.List] = []
    for from_id in list_mapping:
      to_id = list_mapping[from_id]
      from_map_labels.append(from_id)
      to_map_list.append(trello.List(self.dest_board, to_id))
    self.label_to_list_mapping = {}
    for (index, from_map) in enumerate(from_map_labels):
      self.label_to_list_mapping[from_map] = to_map_list[index]

  def prepare_list_mapping(self):
    print('preparing list mappings...')
    list_mapping = self.config.get('list_mapping', {})
    from_map_list: List[trello.List] = []
    to_map_list: List[trello.List] = []
    for from_id in list_mapping:
      to_id = list_mapping[from_id]
      from_map_list.append(trello.List(self.source_board, from_id))
      to_map_list.append(trello.List(self.dest_board, to_id))
    self.list_mapping = {}
    for (index, from_map) in enumerate(from_map_list):
      self.list_mapping[from_map] = to_map_list[index]

  def prepare_label_mapping(self):
    print('preparing label mappings...')
    label_mapping = self.config.get('label_mapping', {})
    from_map_label: List[Label] = []
    to_map_labels: List[List[Label]] = []
    for from_id in label_mapping:
      to_ids = label_mapping[from_id]
      from_map_label.append(Label(self.client, from_id, name='?'))
      to_map_labels.append([Label(self.client, x, name='?') for x in to_ids])
    self.label_mapping = {}
    for (index, from_map) in enumerate(from_map_label):
      self.label_mapping[from_map] = to_map_labels[index]

  def prepare_member_via_label(self):
    print('preparing member via labels...')
    member_mapping = self.config.get('member_via_label', {})
    from_map_label: List[str] = []
    to_map_members: List[List[str]] = []
    for from_id in member_mapping:
      to_ids = member_mapping[from_id]
      from_map_label.append(from_id)
      to_map_members.append(to_ids)
    self.member_via_label = {}
    for (index, item) in enumerate(from_map_label):
      self.member_via_label[item] = to_map_members[index]

  def prepare_comment_via_label(self):
    print('prepare comment via labels')
    member_mapping = self.config.get('comment_via_label', {})
    from_map_label: List[str] = []
    to_map_comment: List[List[str]] = []
    for from_id in member_mapping:
      to_comments = member_mapping[from_id]
      from_map_label.append(from_id)
      to_map_comment.append(to_comments)
    self.comment_via_label = {}
    for (index, item) in enumerate(from_map_label):
      self.comment_via_label[item] = to_map_comment[index]

  def prepare_comment_from_list(self):
    print('preparing comment from list')
    comment_mapping = self.config.get('comment_from_list', {})
    from_map_list: List[str] = []
    to_map_comment: List[List[str]] = []
    for from_id in comment_mapping:
      to_comments = comment_mapping[from_id]
      from_map_list.append(from_id)
      to_map_comment.append(to_comments)
    self.comment_from_list = {}
    for (index, item) in enumerate(from_map_list):
      self.comment_from_list[item] = to_map_comment[index]

  max_batch = 1
  current_batch_index = 0
  max_tasks = 0
  current_task_index = 0

  def update_status(self):
    print('\rBatch: [{0}/{1}] Task: [{2}/{3}]'.format(
      str(self.current_batch_index),
      str(self.max_batch),
      str(self.current_task_index),
      str(self.max_tasks)
    ), end='')

  def run_task_copy(self, card: Card, to_list: trello.List):
    card_labels = card.labels
    if card_labels is None:
      card_labels = []
    # find all labels need to apply after moving
    labels_to_apply: List[Label] = []
    for label in card_labels:
      label_list = self.label_mapping.get(label, [])
      labels_to_apply += label_list
    labels_to_apply = set([x.id for x in labels_to_apply])
    # find all members need to assign after moving
    members_to_assign: List[str] = []
    for label in card_labels:
      member_list = self.member_via_label.get(label.id, [])
      members_to_assign += member_list
    members_to_assign = set(members_to_assign)
    # find all comments need to make after moving
    comments_to_make: List[str] = []
    for label in card_labels:
      comment_list = self.comment_via_label.get(label.id, [])
      comments_to_make += comment_list
    # copy card
    new_card = copy_card(card, to_list, labels_to_apply, members_to_assign)
    # comments
    for comment in comments_to_make:
      new_card.comment(comment)
    if self.config.get('comment_original_card_share_link_to_copied_card', False):
      new_card.comment(card.short_url)
      card.comment(new_card.short_url)
    # remove mapping labels and add label via labels_to_change_with_label_mapping_labels if present
    labels_to_remove = [label for label in card_labels if label.id in self.label_to_list_mapping]
    change_label_mapping = self.config.get('labels_to_change_with_label_mapping_labels', {})
    for label in labels_to_remove:
      card.remove_label(label)
      if change_label_mapping.get(label.id, None):
        try:
          card.add_label(Label(self.client, change_label_mapping.get(label.id, None), ''))
        except:
          pass


  def run_task_move(self, card: Card, to_list: trello.List):
    card_labels = card.labels
    if card_labels is None:
      card_labels = []
    # find all labels need to apply after moving
    labels_to_apply: List[Label] = []
    for label in card_labels:
      label_list = self.label_mapping.get(label, [])
      labels_to_apply += label_list
    # find all members need to assign after moving
    members_to_assign: List[str] = []
    for label in card_labels:
      member_list = self.member_via_label.get(label.id, [])
      members_to_assign += member_list
    # find all comments need to make after moving
    comments_to_make: List[str] = []
    for label in card_labels:
      comment_list = self.comment_via_label.get(label.id, [])
      comments_to_make += comment_list
    # remove all members
    for member in card.idMembers:
      card.unassign(member)
    # remove all labels
    for label in card_labels:
      card.remove_label(label)
    # find comment for list
    comments_via_list = self.comment_from_list.get(card.list_id, [])
    comments_to_make += comments_via_list
    # move card
    card.change_board(to_list.board.id, to_list.id)
    # assign members
    for member in members_to_assign:
      card.assign(member)
    # label
    for label in labels_to_apply:
      try:
        card.add_label(label)
      except:
        pass
    # comment
    for comment in comments_to_make:
      card.comment(comment)

  def run_batch(self, move_list: trello.List):
    pass
    # get card list ( tasks )
    cards = move_list.list_cards()
    # update max_task
    self.max_tasks = len(cards)
    self.update_status()
    # run every task then add to index
    for task in cards:
      if self.config.get('copy_from_source', False):
        self.run_task_copy(task, self.list_mapping[move_list])
      else:
        self.run_task_move(task, self.list_mapping[move_list])
      self.current_task_index += 1
      self.update_status()

  def start_tasks_via_list_mapping(self):
    print('starting tasks...\n\n')
    self.max_batch = len(self.list_mapping)
    self.update_status()
    for batch in self.list_mapping:
      self.run_batch(batch)
      self.current_batch_index += 1
      self.current_task_index = 0
      self.update_status()
    print('\n\n Done!')

  def start_tasks_via_label_to_list_mapping(self):
    print('finding cards...')
    label_to_cards_map: Dict[str: List[Card]] = {}
    for card in self.source_board.all_cards():
      card_labels = card.labels
      if card_labels is None:
        card_labels = []
      for label in card_labels:
        for map_label in self.label_to_list_mapping:
          if label.id == map_label:
            if label_to_cards_map.get(map_label, None) is None:
              label_to_cards_map[map_label] = []
            label_to_cards_map[map_label].append(card)
    print('stating tasks...\n\n')
    self.max_batch = len(label_to_cards_map)
    self.update_status()
    for batch in label_to_cards_map:
      self.current_task_index = 0
      self.max_tasks = len(label_to_cards_map[batch])
      self.update_status()
      for task in label_to_cards_map[batch]:
        self.run_task_copy(task, self.label_to_list_mapping[batch])
        self.current_task_index += 1
        self.update_status()
    print('\n\n Done!')

  def start_bot(self):
    self.prepare_label_mapping()
    self.prepare_member_via_label()
    self.prepare_comment_via_label()
    self.prepare_comment_from_list()
    if self.config.get('label_to_list_mapping', None):
      self.prepare_label_to_list_mapping()
      self.start_tasks_via_label_to_list_mapping()
    else:
      self.prepare_list_mapping()
      self.start_tasks_via_list_mapping()


def main():
  config_path = sys.argv[1]
  with open(config_path, mode='r', encoding="utf-8") as file:
    config = file.read()
  config = json5.loads(config)
  bot = Bot(config)
  bot.start()


if __name__ == "__main__":
  main()
