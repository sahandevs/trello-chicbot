from trello import TrelloClient, Board, Card, Label
import trello
from typing import *
import sys
import json


class Bot:
  config: dict

  client: TrelloClient

  source_board: Board
  dest_board: Board

  list_mapping: Dict[List[trello.List], List[trello.List]]
  label_mapping: Dict[List[Label], List[List[Label]]]

  need_confirmation: bool

  def __init__(self, config: dict):
    self.config = config
    self.need_confirmation = config.get('need_confirmation', False)

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

  def extract_info(self):
    print('extracting info...')
    print('\n\n=============== Source Board: {0}'.format(self.source_board.name))
    Bot.extract_board_info(self.source_board)
    print('\n\n=============== Source Board: {0}'.format(self.dest_board.name))
    Bot.extract_board_info(self.dest_board)

  def start_bot(self):
    pass


def main():
  config_path = sys.argv[1]
  with open(config_path, mode='r') as file:
    config = file.read()
  config = json.loads(config)
  bot = Bot(config)
  bot.start()


if __name__ == "__main__":
  main()
