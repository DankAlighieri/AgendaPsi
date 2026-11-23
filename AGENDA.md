# Agenda e cadastro de consultas

Na branch `cadastroProfissional`, a tabela `Agenda` representa horários de início
oferecidos por cada psicólogo. Cada par de profissional e data/hora é único.

## Executar

Com as dependências de `requirements.txt` instaladas:

```powershell
python manage.py migrate
python manage.py runserver
```

1. Acesse `/` e selecione um profissional, ou cadastre um profissional em
   `/cadastroProfissional/`.
2. Cadastre os pacientes no Django Admin (`/admin/`), vinculando cada paciente ao
   profissional correspondente.
3. Clique no nome do profissional, selecione o cliente e um horário livre e envie.
4. Use **Ver agenda** para consultar os horários livres e ocupados.

Os horários são criados automaticamente para os próximos 30 dias, de segunda a
sexta, das 8h às 12h e das 14h às 18h. São oferecidas consultas de uma hora, com
início às 8h, 9h, 10h, 11h, 14h, 15h, 16h e 17h. Não é necessário cadastrar
horários manualmente. A janela de 30 dias avança conforme a data atual.

O formulário lista somente os pacientes do profissional e os horários futuros
sem consulta ativa. A consulta salva referencia o horário da agenda. A ocupação
é calculada a partir das consultas, evitando manter um campo booleano separado.
Uma restrição no banco impede duas consultas não canceladas no mesmo horário.
Consultas anteriores, ainda sem vínculo com `Agenda`, também bloqueiam seu horário.
Cancelar uma consulta pelo Admin libera seu horário, desde que não exista outra
consulta não cancelada naquela data e hora.

Os horários usam `America/Sao_Paulo`. Horários cadastrados anteriormente fora da
grade padrão não são oferecidos para novas reservas. As consultas existentes
continuam preservadas. A duração de uma hora é a convenção da grade; consultas
antigas fora da grade não têm duração cadastrada e bloqueiam seu início exato.

O projeto ainda não associa profissionais a usuários autenticados. A seleção do
profissional segue a estrutura atual, por URL, sem controle de acesso individual.

## Google Agenda (futuro)

Nenhuma chamada ao Google é feita. O campo já existente `Consulta.google_event_id`
foi preservado para a futura integração. O ponto central de agendamento local é
`agenda.services.agendar_consulta`; a sincronização futura deverá ocorrer após a
confirmação da transação local e tratar falhas e novas tentativas.

## Verificar

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test agenda
```

Os testes usam um banco separado. A migração do banco local deve ser executada
com `python manage.py migrate` antes de utilizar as novas páginas.
