## Usage

```
git clone https://github.com/SahandAkbarzadeh/trello-chicbot.git
cd trello-chicbot
python -m pip install requirement.txt
python run.py "configFile.json"
```

## Config File

[Sample Config File](./sampleConfig.json)

|Name|Usage|
|---|---|
|source_board|string that contains in source board name|
|destination_board|string that contains in destination board name|
|extract_board_info|this will extract all information needed (member, board, list ids) for the bot configuration |
|copy_from_source|if enabled insted of moving a card it will copy a card to destination|
|comment_original_card_share_link_to_copied_card|when enabled with `copy_from_source` it will comment the original card link|
|labels_to_change_with_label_mapping_labels|(string: labelId (source)) to (list: labelId (destination) mapping|
|api_key|your trello api key|
|api_secret|your trello secret key|
|label_to_list_mapping|(string: labelId (source)) to (string: trelloListId (destination) mapping|
|list_mapping|(string: listId (source)) to (string: listId (destination)) mapping|
|comment_from_list|(string: listId (source) to list of comments (string)). comment if the card is in the list|
|label_mapping|(string: labelId (source) to (list: labelId (destination)) remove old labels and put new labels|
|member_via_label|(string: labelId (source) to (list: memberId (destination)) remove old members and assign new members|
|comment_via_label|(string: labelId (source) to list of comments (string)). comment if the card has the label|
