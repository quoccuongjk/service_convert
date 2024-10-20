from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
import yaml
import os
from .serializers import ChatRequestSerializer
from .train_intent import get_intent_from_question

class ChatbotAPIView(APIView):
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if serializer.is_valid():
            question = serializer.validated_data['question']
            answer = serializer.validated_data['answer']

            # Tải intents từ API thay vì từ CSV
            intents = self.get_intents_from_api()  # Thực hiện phương thức này

            # Xử lý dữ liệu đầu vào
            self.process_data(intents, question, answer)

            return Response({"message": "Dữ liệu đã được xử lý thành công"}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_intents_from_api(self):
        # Thay thế bằng cuộc gọi API thực tế để lấy intents
        return []

    def process_data(self, intents, user_example, bot_response):
        # Đường dẫn đến các tệp intent
        intent_files = {
            'booking': '../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/data/booking.yml',
            'doctor': '../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/data/doctor.yml',
            'clinic': '../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/data/clinic.yml',
            'hospital': '../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/data/hospital.yml',
            'symptom': '../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/data/symptom.yml',
            'consultant': '../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/data/consultant.yml',
            'patient': '../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/data/patient.yml',
            'health': '../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/data/health.yml'
        }

        def read_examples_from_file(file_path):
            examples = set()
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                    if data and 'nlu' in data:
                        for item in data['nlu']:
                            examples.update(item['examples'].splitlines())
            return examples

        # Nhận câu hỏi và câu trả lời từ người dùng
        question = user_example
        bot_response = bot_response

        # Xác định intent từ câu hỏi
        intent = get_intent_from_question(question)

        if intent in intent_files:
            file_path = intent_files[intent]
            existing_examples = read_examples_from_file(file_path)
        
            if question.strip() not in {example.lstrip('- ').strip() for example in existing_examples}:
                with open(file_path, 'a', encoding='utf-8') as file:
                    file.write(f"    - {question.strip()}\n")

        responses = {f'utter_{intent}': [{'text': bot_response}]}

        domain_data = {
            'intents': [],
            'responses': {}
        }

        if os.path.exists('../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/domain.yml'):
            with open('../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/domain.yml', 'r', encoding='utf-8') as domain_file:
                domain_data = yaml.safe_load(domain_file) or {}

        existing_intents = set(domain_data.get('intents', []))
        existing_intents.add(intent)
        domain_data['intents'] = list(existing_intents)

        for intent, response_list in responses.items():
            if intent not in domain_data.get('responses', {}):
                domain_data.setdefault('responses', {})[intent] = []
                
            for response in response_list:
                if response not in domain_data['responses'][intent]:
                    domain_data['responses'][intent].append(response)

        with open('../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/domain.yml', 'w', encoding='utf-8') as domain_file:
            domain_file.write("version: \"3.1\"\n\n")
            domain_file.write("intents:\n")
            for intent in domain_data['intents']:
                domain_file.write(f"  - {intent}\n")
            
            domain_file.write("\nresponses:\n")
            for intent, response_list in domain_data['responses'].items():
                domain_file.write(f"  {intent}:\n")
                for response in response_list:
                    domain_file.write(f"  - text: \"{response['text']}\"\n") 

        stories_data = []
        existing_intents = set()  
        added_intents = set() 

        existing_stories = []
        if os.path.exists('../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/data/stories.yml'):
            with open('../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/data/stories.yml', 'r', encoding='utf-8') as stories_file:
                existing_data = yaml.safe_load(stories_file)
                if existing_data and 'stories' in existing_data:
                    existing_stories = existing_data['stories']
                    # Lưu tất cả các intent đã có
                    for story in existing_stories:
                        for step in story['steps']:
                            intent = step.get('intent')
                            if intent:
                                existing_intents.add(intent)

        
        intent = get_intent_from_question(question)
        action = f'utter_{intent}'

            # Kiểm tra xem intent đã tồn tại hay chưa
        if intent not in existing_intents and intent not in added_intents:
            stories_data.append({
                'story': f'story_{intent}', 
                'steps': [
                    {'intent': intent},
                    {'action': action}
                ]
            })
            added_intents.add(intent)  # Đánh dấu intent này đã được thêm


        # Ghi theo định dạng dễ định dạng hơn
        with open('../../../ai-chatbot-rasa-en/ai-chatbot-rasa-en/data/stories.yml', 'a', encoding='utf-8') as stories_file:
            for story in stories_data:
                stories_file.write(f"- story: {story['story']}\n")
                stories_file.write("  steps:\n")
                for step in story['steps']:
                    if 'intent' in step:
                        stories_file.write(f"  - intent: {step['intent']}\n")
                    if 'action' in step:
                        stories_file.write(f"  - action: {step['action']}\n")
