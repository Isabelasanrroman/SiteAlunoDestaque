from flask import Flask, render_template, request, redirect, url_for, session, flash
import csv
from collections import defaultdict
import psycopg2

def conectar():
    return psycopg2.connect(
        host="localhost",
        database="alunosdestaques",
        user="postgres",
        password="1234"
    )

app = Flask(__name__)
app.secret_key = 'chave_secreta_para_sessoes'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/entrar', methods=['GET', 'POST'])
def entrar():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        conn = conectar()
        cur = conn.cursor()
        cur.execute("SELECT id_professor, nome FROM professor WHERE email = %s AND senha = %s", (email, senha))
        professor = cur.fetchone()
        cur.close()
        conn.close()

        if professor:
            session['professor_id'] = professor[0]
            session['professor_nome'] = professor[1]
            return redirect(url_for('cursos_cadastrados'))
        else:
            return("E-mail ou senha incorretos! Cadastre-se primeiro.")
            
    return render_template('entrar.html')

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        
        conn = conectar()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO professor (nome, email, senha) VALUES (%s, %s, %s)", (nome, email, senha))
            conn.commit()
            return redirect(url_for('entrar'))
        except Exception as e:
            conn.rollback()
            return f"Erro ao cadastrar: {e}"
        finally:
            cur.close()
            conn.close()
            
    return render_template('cadastrar.html')

@app.route('/cadastrar-turmas', methods=['GET', 'POST'])
def cadastrar_turmas():
    if 'professor_id' not in session:
        return redirect(url_for('entrar'))

    if request.method == 'POST':
        nome_turma_form = request.form['turma']
        arquivo = request.files['arquivo']

        if not arquivo:
            return "Por favor, envie um arquivo."

        conteudo = arquivo.stream.read().decode("utf-8-sig").splitlines()
        leitor = csv.DictReader(conteudo, delimiter=';')

        dados_alunos = defaultdict(lambda: {"disciplinas": []})

        for linha in leitor:
            print(linha)
            try:
                nome = linha.get('nome', '').strip()
                disc = linha.get('disciplina', '').strip()
                n = float(linha.get('nota', '0').replace(',', '.'))
                f = float(linha.get('frequência', linha.get('frequencia', '0')).replace(',', '.'))
                
                dados_alunos[nome]["disciplinas"].append({
                    "nome": disc, "nota": n, "freq": f
                })
            except Exception as e:
                print(f"Erro ao ler linha: {e}")

        conn = conectar()
        cur = conn.cursor()

        try:
            id_prof = session['professor_id']

            cur.execute("""
                INSERT INTO turma (nome_turma, id_curso, id_professor) 
                VALUES (%s, 1, %s) RETURNING id_turma
            """, (nome_turma_form, id_prof))
            id_turma = cur.fetchone()[0]

            lista_para_frontend = []

            for nome_aluno, info in dados_alunos.items():
                notas = [d['nota'] for d in info['disciplinas']]
                freqs = [d['freq'] for d in info['disciplinas']]
                media_geral = sum(notas) / len(notas)
                freq_geral = sum(freqs) / len(freqs)

                if media_geral >= 95 and freq_geral == 100: classif = "🥇 Ouro"
                elif media_geral >= 95 and freq_geral >= 97: classif = "🥈 Prata"
                elif media_geral >= 95 and freq_geral >= 95: classif = "🥉 Bronze"
                else: classif = "—"

                cur.execute("INSERT INTO aluno (nome, id_turma) VALUES (%s, %s) RETURNING id_aluno", 
                           (nome_aluno, id_turma))
                id_aluno = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO boletim (id_aluno, media_geral, frequencia_geral, classificacao)
                    VALUES (%s, %s, %s, %s) RETURNING id_boletim
                """, (id_aluno, media_geral, freq_geral, classif))
                id_boletim = cur.fetchone()[0]

                for d in info['disciplinas']:
                    cur.execute("""
                        INSERT INTO nota (id_boletim, disciplina, nota, frequencia)
                        VALUES (%s, %s, %s, %s)
                    """, (id_boletim, d['nome'], d['nota'], d['freq']))

                lista_para_frontend.append({
                    "nome": nome_aluno,
                    "media": f"{media_geral:.1f}".replace('.', ','),
                    "freq": f"{freq_geral:.1f}".replace('.', ','),
                    "classificacao": classif,
                    "media_num": media_geral,
                })

            conn.commit()
            lista_para_frontend.sort(key=lambda x: (x["media_num"], float(x["freq"].replace(',', '.'))), reverse=True)
            return render_template("classificacao.html", alunos=lista_para_frontend, turma=nome_turma_form)

        except Exception as e:
            conn.rollback()
            return f"Erro no banco de dados: {e}"
        finally:
            cur.close()
            conn.close()

    return render_template("cadastrarturmas.html")

@app.route('/cursos-cadastrados')
def cursos_cadastrados():
    if 'professor_id' not in session:
        return redirect(url_for('entrar'))
    
    id_prof = session['professor_id']
    nome_prof = session.get('professor_nome', 'Professor')

    conn = conectar()
    cur = conn.cursor()
    
    cur.execute("SELECT id_turma, nome_turma FROM turma WHERE id_professor = %s", (id_prof,))
    turmas_do_banco = cur.fetchall()
    
    cur.close()
    conn.close()

    lista_turmas = []
    for t in turmas_do_banco:
        lista_turmas.append({
            "id": t[0],
            "nome": t[1]
        })

    return render_template('cursoscadastrados.html', turmas=lista_turmas, nome_professor=nome_prof)

@app.route('/classificacao/<int:id_turma>')
def ver_classificacao(id_turma):

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT a.nome, b.media_geral, b.frequencia_geral, b.classificacao
        FROM aluno a
        JOIN boletim b ON a.id_aluno = b.id_aluno
        WHERE a.id_turma = %s
        ORDER BY b.media_geral DESC
    """, (id_turma,))

    resultados = cur.fetchall()

    cur.execute("SELECT nome_turma FROM turma WHERE id_turma = %s", (id_turma,))
    turma = cur.fetchone()[0]

    cur.close()
    conn.close()

    alunos = []

    for r in resultados:
        alunos.append({
            "nome": r[0],
            "media": f"{r[1]:.1f}".replace('.', ','),
            "freq": f"{r[2]:.1f}".replace('.', ','),
            "classificacao": r[3]
        })

    return render_template("classificacao.html", alunos=alunos, turma=turma)

if __name__ == '__main__':
    app.run(debug=True)