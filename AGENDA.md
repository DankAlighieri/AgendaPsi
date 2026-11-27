# Agenda e cadastro de consultas

A tabela `Agenda` representa horários de início oferecidos por cada psicólogo.
Cada par de profissional e data/hora é único.

## Executar

Requer Python 3.12 ou superior. No Windows, o script cria o ambiente virtual em
`.venv`, instala as dependências e aplica as migrações:

```powershell
.\scripts\bootstrap.ps1
```

Se o PowerShell bloquear a execução de scripts:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

Depois, inicie o servidor:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Os demais comandos `python` deste documento usam o mesmo interpretador do
`.venv`. Sem o script, instale com `pip install -r requirements.txt` e rode
`python manage.py migrate`.

1. Cadastre um profissional em `/cadastroProfissional/` e entre em `/login/`.
2. Cadastre os pacientes em `/cadastroPaciente`.
3. Em **Cadastrar nova consulta**, selecione o paciente e um horário livre.
4. A página inicial e `/agenda/` mostram os horários livres e ocupados.

## Acesso e isolamento

Cada `Profissional` tem obrigatoriamente um `User`; o e-mail em minúsculas é o
`username`. As páginas do profissional usam `@profissional_required`, e o dono
dos dados vem sempre da sessão (`request.profissional`). Nenhuma URL ou
formulário aceita `profissional_id`.

O e-mail e o telefone podem ser alterados em `/updatePerfil`; o e-mail de login
acompanha a mudança. O CRP não é editável e é salvo só com dígitos: 2 da região
mais 4 a 6 do registro.

Toda página nova com dados do profissional precisa de um teste de acesso
cruzado: criar dois profissionais com `User` e verificar que um não lê nem
altera os dados do outro (veja `IsolamentoTests` em `agenda/tests.py`). Rotas
que recebam o id de um registro devem filtrar pelo profissional da sessão e
responder 404 para registro alheio.

### Profissionais antigos

A migração `0010` cria um usuário para cada profissional que não tinha, sem
senha utilizável. Para liberar o acesso, defina a senha (o usuário é o e-mail):

```powershell
python manage.py changepassword email@exemplo.com
```

## Pacientes

Só nome e telefone são obrigatórios. CPF, e-mail e data de nascimento são
opcionais, mas validados quando informados. O telefone precisa de DDD.

## Horários

A grade padrão é criada automaticamente para os próximos 30 dias, de segunda a
sexta, com início às 8h, 9h, 10h, 11h, 14h, 15h, 16h e 17h. A janela avança
conforme a data atual.

Em **Cadastrar horários na agenda**, o profissional acrescenta horários em
qualquer dia e hora futuros, um a um ou em lote semanal (até 52 semanas):

- um horário gerado pela grade não conta como conflito: o cadastro o assume;
- um horário já cadastrado manualmente ou por lote é conflito;
- o lote é tudo ou nada e lista as datas em conflito;
- reenviar o mesmo lote não duplica horários.

O sistema não registra a duração de cada horário e só impede dois inícios iguais.
Horários manuais próximos (por exemplo, 8h e 8h30) podem se sobrepor.

## Consultas

O formulário lista os pacientes do profissional e todos os horários futuros sem
consulta ativa. A consulta salva referencia o horário da agenda. A ocupação é
calculada a partir das consultas, sem campo booleano separado. Uma restrição no
banco impede duas consultas não canceladas no mesmo horário. Consultas antigas,
sem vínculo com `Agenda`, também bloqueiam seu horário. Cancelar uma consulta
pelo Admin libera o horário, desde que não exista outra consulta ativa nele.

Os horários usam `America/Sao_Paulo`.

## Dados de teste

```powershell
python manage.py popular_banco --senha "defina-uma-senha"
```

`seed_fake_data` gera uma carga maior; `--clear` apaga antes os dados da agenda.
Sem `--senha`, os profissionais criados não conseguem entrar.

## Google Agenda (futuro)

Nenhuma chamada ao Google é feita. O campo `Consulta.google_event_id` foi
preservado para a futura integração. O ponto central de agendamento local é
`agenda.services.agendar_consulta`; a sincronização futura deverá ocorrer após a
confirmação da transação local e tratar falhas e novas tentativas.

## Verificar

```powershell
python manage.py check
```

```powershell
python manage.py makemigrations --check --dry-run
```

```powershell
python manage.py test agenda
```
